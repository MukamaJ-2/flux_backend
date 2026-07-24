from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from finances.models import Loan, Request
from finances.views import LoanViewSet, RequestViewSet
from groups.models import Group, Membership

User = get_user_model()


class RoleWorkflowTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.group = Group.objects.create(
            id='group-test',
            name='Test Group',
            contribution=20000,
            invite_code='TEST1234',
        )

        self.member = User.objects.create_user(
            username='member', email='member@example.com', password='secret123', role='member'
        )
        self.secretary = User.objects.create_user(
            username='secretary', email='secretary@example.com', password='secret123', role='secretary'
        )
        self.treasury = User.objects.create_user(
            username='treasury', email='treasury@example.com', password='secret123', role='treasury'
        )
        self.audit = User.objects.create_user(
            username='audit', email='audit@example.com', password='secret123', role='audit'
        )
        self.chair = User.objects.create_user(
            username='chair', email='chair@example.com', password='secret123', role='chair'
        )

        for user in [self.member, self.secretary, self.treasury, self.audit, self.chair]:
            Membership.objects.create(user=user, group=self.group, role='member')

    def _make_request(self, status='pending_secretary'):
        return Request.objects.create(
            id='req-test-1',
            group=self.group,
            requester=self.member,
            type='contribution',
            amount=100000,
            title='Monthly contribution',
            status=status,
        )

    def _make_loan(self, status='pending_secretary'):
        return Loan.objects.create(
            id='loan-test-1',
            group=self.group,
            requester=self.member,
            title='Emergency loan',
            amount=500000,
            status=status,
        )

    def test_secretary_can_advance_request_to_treasury(self):
        request_obj = self._make_request(status='pending_secretary')
        request = self.factory.post('/', {'approved': True})
        force_authenticate(request, self.secretary)

        response = RequestViewSet.as_view({'post': 'advance'})(request, pk=request_obj.id)

        self.assertEqual(response.status_code, 200)
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, 'pending_treasury')

    def test_treasury_can_advance_loan_to_audit(self):
        loan = self._make_loan(status='pending_treasury')
        request = self.factory.post('/', {'approved': True})
        force_authenticate(request, self.treasury)

        response = LoanViewSet.as_view({'post': 'advance'})(request, pk=loan.id)

        self.assertEqual(response.status_code, 200)
        loan.refresh_from_db()
        self.assertEqual(loan.status, 'pending_audit')
