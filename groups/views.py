import uuid

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from users.permissions import has_permission, can_manage_group
from .models import Group, Membership
from .serializers import GroupSerializer, MembershipSerializer

User = get_user_model()


def is_group_admin(user, group):
    return Membership.objects.filter(user=user, group=group, role='admin').exists()


class GroupViewSet(viewsets.ModelViewSet):
    """
    Groups CRUD.
    - List scoped to groups the current user is a member of.
    - On create, creator automatically becomes admin member.
    - Extra actions: join, members management.
    """
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(memberships__user=self.request.user).distinct()

    def perform_create(self, serializer):
        if not has_permission(self.request.user, 'create_group'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Your role cannot create groups.')
        group = serializer.save()
        Membership.objects.create(user=self.request.user, group=group, role='admin')

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        if not can_manage_group(request.user, group):
            return Response({'error': 'Only chair or group admins can delete this group.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        group = self.get_object()
        if not can_manage_group(request.user, group):
            return Response({'error': 'Only chair or group admins can update group settings.'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='join')
    def join(self, request):
        """
        POST /api/groups/join/
        Body: { "inviteCode": "ABCD1234" }
        Joins the group associated with the invite code.
        """
        invite_code = request.data.get('inviteCode', '').strip().upper()
        if not invite_code:
            return Response({'error': 'inviteCode is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(invite_code=invite_code)
        except Group.DoesNotExist:
            return Response({'error': 'Invalid invite code. No group found.'}, status=status.HTTP_404_NOT_FOUND)

        membership, created = Membership.objects.get_or_create(
            user=request.user,
            group=group,
            defaults={'role': 'member'},
        )

        if not created:
            return Response({'error': 'You are already a member of this group.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = GroupSerializer(group, context={'request': request})
        return Response({'success': True, 'group': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='members')
    def add_member(self, request, pk=None):
        """
        POST /api/groups/{id}/members/
        Body: { "email": "user@example.com", "name": "Full Name" }
        Admin only. Finds existing user by email or creates a stub user, then adds to group.
        """
        group = self.get_object()
        if not can_manage_group(request.user, group) and not has_permission(request.user, 'onboard_members'):
            return Response({'error': 'Only chair or mobilizer can add members.'}, status=status.HTTP_403_FORBIDDEN)

        email = request.data.get('email', '').strip().lower()
        name = request.data.get('name', '').strip()

        if not email:
            return Response({'error': 'email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Try to find existing user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Create a stub/placeholder user
            parts = name.split(' ', 1)
            first_name = parts[0] if parts else name
            last_name = parts[1] if len(parts) > 1 else ''
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            default_password = get_random_string(20)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=default_password,
                first_name=first_name,
                last_name=last_name,
                avatar=name[:2].upper() if name else email[:2].upper(),
                must_change_password=True,
            )
        else:
            default_password = None

        membership, created = Membership.objects.get_or_create(
            user=user,
            group=group,
            defaults={'role': 'member'},
        )

        if not created:
            return Response({'error': f'{email} is already a member of this group.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MembershipSerializer(membership)
        response_data = serializer.data
        if default_password:
            response_data['default_password'] = default_password

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete', 'patch'], url_path='members/(?P<member_id>[^/.]+)')
    def manage_member(self, request, pk=None, member_id=None):
        """
        DELETE /api/groups/{id}/members/{member_id}/  — Admin ejects a member.
        PATCH  /api/groups/{id}/members/{member_id}/  — Admin edits name/email.
        """
        group = self.get_object()
        if not can_manage_group(request.user, group):
            return Response({'error': 'Only chair or group admins can manage members.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            membership = Membership.objects.get(user_id=member_id, group=group)
        except Membership.DoesNotExist:
            return Response({'error': 'Member not found in this group.'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'DELETE':
            if membership.role == 'admin':
                return Response({'error': 'Cannot eject the group admin.'}, status=status.HTTP_400_BAD_REQUEST)
            membership.delete()
            return Response({'success': True}, status=status.HTTP_200_OK)

        # PATCH — edit name / email
        user = membership.user
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip().lower()

        if name:
            parts = name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''

        if email and email != user.email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response({'error': 'This email is already in use by another account.'}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email

        user.save()
        serializer = MembershipSerializer(membership)
        return Response(serializer.data)
