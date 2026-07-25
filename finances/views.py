import uuid
from datetime import datetime

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from groups.models import Group, Membership
from .models import Request, Record, Loan, Goal
from .serializers import RequestSerializer, RecordSerializer, LoanSerializer, GoalSerializer


def is_group_admin(user, group):
    """Check if user is an admin (role='admin') in the given group's Membership."""
    return Membership.objects.filter(user=user, group=group, role='admin').exists()


def make_id(prefix=''):
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def can_handle_finance(user, group=None):
    """Return True when a user can process finance workflow steps."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    if getattr(user, 'role', '') == 'sysadmin':
        return True

    if getattr(user, 'role', '') in {'chair', 'treasury', 'secretary', 'audit'}:
        return True

    return group is not None and is_group_admin(user, group)


class RequestViewSet(viewsets.ModelViewSet):
    """
    Contribution and investment requests.
    - List/Create scoped to groups the user belongs to.
    - decide/ action: Admin approves/rejects. Approval auto-creates a Record.
    - vote/ action: Any member casts yes/no on a 'proposed' investment.
    """
    serializer_class = RequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Get all groups the user is a member of
        user_group_ids = Membership.objects.filter(user=user).values_list('group_id', flat=True)
        qs = Request.objects.filter(group_id__in=user_group_ids)

        # Optional: filter by group_id query param
        group_id = self.request.query_params.get('group')
        if group_id:
            qs = qs.filter(group_id=group_id)

        return qs

    def perform_create(self, serializer):
        req_id = self.request.data.get('id') or make_id('req-')
        initial_status = 'proposed' if self.request.data.get('type') == 'investment' else 'pending_secretary'
        serializer.save(
            id=req_id,
            requester=self.request.user,
            status=initial_status,
        )

    def _advance_request(self, request_obj, user, approved):
        role = getattr(user, 'role', '')
        next_status = None

        if request_obj.status == 'pending_secretary' and role == 'secretary':
            next_status = 'pending_treasury'
        elif request_obj.status == 'pending_treasury' and role == 'treasury':
            next_status = 'pending_audit'
        elif request_obj.status == 'pending_audit' and role == 'audit':
            next_status = 'pending_chair'
        elif request_obj.status == 'pending_chair' and role == 'chair':
            next_status = 'approved' if approved else 'rejected'

        if next_status is None:
            raise PermissionDenied('This role cannot advance this request at the current stage.')

        request_obj.status = next_status
        request_obj.decided_by = ' '.join(p for p in [user.first_name, user.last_name] if p) or user.email
        request_obj.decided_at = datetime.utcnow()
        request_obj.save()

        return request_obj

    @action(detail=True, methods=['post'], url_path='decide')
    def decide(self, request, pk=None):
        """
        POST /api/requests/{id}/decide/
        Body: { "approved": true/false }
        Workflow-based approval for secretary, treasury, audit, and chair.
        """
        req_obj = self.get_object()
        group = req_obj.group

        if not can_handle_finance(request.user, group):
            return Response({'error': 'You do not have permission to decide this request.'}, status=status.HTTP_403_FORBIDDEN)

        approved = request.data.get('approved', False)
        req_obj = self._advance_request(req_obj, request.user, approved)

        # Auto-create an official Record on contribution approval
        if approved and req_obj.status == 'approved' and req_obj.type == 'contribution':
            Record.objects.create(
                id=make_id('rec-'),
                group=group,
                member=req_obj.requester,
                amount=req_obj.amount,
                method=req_obj.method or 'Member Request',
                note=req_obj.note or req_obj.title,
                receipt_url=req_obj.receipt_url,
            )

        serializer = self.get_serializer(req_obj)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='advance')
    def advance(self, request, pk=None):
        req_obj = self.get_object()
        group = req_obj.group
        if not can_handle_finance(request.user, group):
            return Response({'error': 'You do not have permission to advance this request.'}, status=status.HTTP_403_FORBIDDEN)

        approved = request.data.get('approved', False)
        req_obj = self._advance_request(req_obj, request.user, approved)
        serializer = self.get_serializer(req_obj)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='vote')
    def vote(self, request, pk=None):
        """
        POST /api/requests/{id}/vote/
        Body: { "vote": "yes" | "no" }
        Any group member can vote on a 'proposed' investment request.
        Auto-advances to 'pending_audit' if majority reached.
        """
        req_obj = self.get_object()
        group = req_obj.group

        # Verify membership
        if not Membership.objects.filter(user=request.user, group=group).exists():
            return Response({'error': 'You are not a member of this group.'}, status=status.HTTP_403_FORBIDDEN)

        if req_obj.status != 'proposed':
            return Response({'error': 'Voting is only allowed on proposed requests.'}, status=status.HTTP_400_BAD_REQUEST)

        vote_type = request.data.get('vote', '').lower()
        if vote_type not in ('yes', 'no'):
            return Response({'error': 'vote must be "yes" or "no".'}, status=status.HTTP_400_BAD_REQUEST)

        user_id = str(request.user.id)
        votes = req_obj.votes or {'yes': [], 'no': []}

        # Remove any prior vote from this user
        votes['yes'] = [v for v in votes.get('yes', []) if v != user_id]
        votes['no'] = [v for v in votes.get('no', []) if v != user_id]

        votes[vote_type].append(user_id)
        req_obj.votes = votes

        # Check majority
        total_members = Membership.objects.filter(group=group).count()
        majority = (total_members // 2) + 1
        if len(votes['yes']) >= majority:
            req_obj.status = 'pending_audit'

        req_obj.save()
        serializer = self.get_serializer(req_obj)
        return Response(serializer.data)


class RecordViewSet(viewsets.ModelViewSet):
    """
    Contribution records. Scoped to the user's groups.
    Admin can directly create records (manual entry).
    """
    serializer_class = RecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_group_ids = Membership.objects.filter(user=user).values_list('group_id', flat=True)
        qs = Record.objects.filter(group_id__in=user_group_ids)

        group_id = self.request.query_params.get('group')
        if group_id:
            qs = qs.filter(group_id=group_id)

        return qs

    def perform_create(self, serializer):
        rec_id = self.request.data.get('id') or make_id('rec-')
        group_id = self.request.data.get('group')
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            raise ValidationError({'group': 'Invalid group.'})

        if not can_handle_finance(self.request.user, group):
            raise PermissionDenied('Only finance roles can directly create records.')

        # Resolve member — if 'member' field not given, use the request user
        member_id = self.request.data.get('member')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            member = User.objects.get(id=member_id) if member_id else self.request.user
        except User.DoesNotExist:
            member = self.request.user

        serializer.save(id=rec_id, member=member)


class LoanViewSet(viewsets.ModelViewSet):
    """
    Loan requests. Members submit, admins decide.
    """
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_group_ids = Membership.objects.filter(user=user).values_list('group_id', flat=True)
        qs = Loan.objects.filter(group_id__in=user_group_ids)

        group_id = self.request.query_params.get('group')
        if group_id:
            qs = qs.filter(group_id=group_id)

        return qs

    def perform_create(self, serializer):
        loan_id = self.request.data.get('id') or make_id('loan-')
        serializer.save(
            id=loan_id,
            requester=self.request.user,
            status='pending_secretary',
        )

    def _advance_loan(self, loan, user, approved):
        role = getattr(user, 'role', '')
        next_status = None

        if loan.status == 'pending_secretary' and role == 'secretary':
            next_status = 'pending_treasury'
        elif loan.status == 'pending_treasury' and role == 'treasury':
            next_status = 'pending_audit'
        elif loan.status == 'pending_audit' and role == 'audit':
            next_status = 'pending_chair'
        elif loan.status == 'pending_chair' and role == 'chair':
            next_status = 'approved' if approved else 'rejected'

        if next_status is None:
            raise PermissionDenied('This role cannot advance this loan at the current stage.')

        loan.status = next_status
        loan.decided_by = ' '.join(p for p in [user.first_name, user.last_name] if p) or user.email
        loan.decided_at = datetime.utcnow()
        loan.save()

        return loan

    @action(detail=True, methods=['post'], url_path='decide')
    def decide(self, request, pk=None):
        """
        POST /api/loans/{id}/decide/
        Body: { "approved": true/false }
        Workflow-based approval for secretary, treasury, audit, and chair.
        """
        loan = self.get_object()
        group = loan.group

        if not can_handle_finance(request.user, group):
            return Response({'error': 'You do not have permission to decide this loan.'}, status=status.HTTP_403_FORBIDDEN)

        approved = request.data.get('approved', False)
        loan = self._advance_loan(loan, request.user, approved)

        serializer = self.get_serializer(loan)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='advance')
    def advance(self, request, pk=None):
        loan = self.get_object()
        group = loan.group
        if not can_handle_finance(request.user, group):
            return Response({'error': 'You do not have permission to advance this loan.'}, status=status.HTTP_403_FORBIDDEN)

        approved = request.data.get('approved', False)
        loan = self._advance_loan(loan, request.user, approved)
        serializer = self.get_serializer(loan)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='repay')
    def repay(self, request, pk=None):
        """
        PATCH /api/loans/{id}/repay/
        Body: { "amount": 50000 }
        Updates the repaid amount on a loan.
        """
        loan = self.get_object()
        amount = request.data.get('amount', 0)
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

        loan.repaid = float(loan.repaid) + amount
        if loan.repaid >= float(loan.amount):
            loan.status = 'repaid'
        loan.save()

        serializer = self.get_serializer(loan)
        return Response(serializer.data)


class GoalViewSet(viewsets.ModelViewSet):
    """
    Savings goals. Each user manages their own. Admins can decide pending goals.
    """
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Admins can see all goals in their groups; members see their own
        user_group_ids = Membership.objects.filter(user=user).values_list('group_id', flat=True)
        admin_group_ids = Membership.objects.filter(user=user, role='admin').values_list('group_id', flat=True)

        # Goals either owned by user, or linked to a group where user is admin
        from django.db.models import Q
        qs = Goal.objects.filter(
            Q(user=user) | Q(linked_group_id__in=admin_group_ids)
        )

        group_id = self.request.query_params.get('group')
        if group_id:
            qs = qs.filter(linked_group_id=group_id)

        return qs

    def perform_create(self, serializer):
        goal_id = self.request.data.get('id') or make_id('goal-')
        linked_group_id = self.request.data.get('linkedGroupId') or self.request.data.get('linked_group')
        linked_group = None
        if linked_group_id:
            try:
                linked_group = Group.objects.get(id=linked_group_id)
            except Group.DoesNotExist:
                pass

        serializer.save(
            id=goal_id,
            user=self.request.user,
            linked_group=linked_group,
            status='pending',
        )

    @action(detail=True, methods=['post'], url_path='decide')
    def decide(self, request, pk=None):
        """
        POST /api/goals/{id}/decide/
        Body: { "approved": true/false }
        Admin of the linked group can decide. If no linked group, only sysadmin.
        """
        goal = self.get_object()
        approved = request.data.get('approved', False)

        # Check permission
        can_decide = False
        if goal.linked_group:
            can_decide = is_group_admin(request.user, goal.linked_group)
        if request.user.role == 'sysadmin':
            can_decide = True

        if not can_decide:
            return Response({'error': 'Only group admins can decide goals.'}, status=status.HTTP_403_FORBIDDEN)

        admin_name_parts = [request.user.first_name, request.user.last_name]
        admin_name = ' '.join(p for p in admin_name_parts if p) or request.user.email

        goal.status = 'approved' if approved else 'rejected'
        goal.decided_by = admin_name
        goal.decided_at = datetime.utcnow()
        goal.save()

        serializer = self.get_serializer(goal)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='save')
    def save_progress(self, request, pk=None):
        """
        PATCH /api/goals/{id}/save/
        Body: { "amount": 50000 }
        Adds to the savedAmount of a goal.
        """
        goal = self.get_object()
        if goal.user != request.user:
            return Response({'error': 'You can only update your own goals.'}, status=status.HTTP_403_FORBIDDEN)

        amount = request.data.get('amount', 0)
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

        goal.saved_amount = float(goal.saved_amount) + amount
        if goal.saved_amount >= float(goal.target_amount):
            goal.status = 'completed'
        goal.save()

        serializer = self.get_serializer(goal)
        return Response(serializer.data)
