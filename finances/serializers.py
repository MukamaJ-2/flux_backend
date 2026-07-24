from rest_framework import serializers
from .models import Request, Record, Loan, Goal
from users.serializers import UserSerializer


class RequestSerializer(serializers.ModelSerializer):
    requesterName = serializers.SerializerMethodField()
    requesterId = serializers.CharField(source='requester.id', read_only=True)
    requesterAvatar = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    decidedAt = serializers.DateTimeField(source='decided_at', read_only=True)
    decidedBy = serializers.CharField(source='decided_by', read_only=True)
    receiptUrl = serializers.URLField(source='receipt_url', required=False, allow_blank=True)

    class Meta:
        model = Request
        fields = [
            'id', 'group', 'type', 'amount', 'title', 'method', 'note',
            'status', 'receiptUrl', 'receipt_url', 'votes',
            'createdAt', 'decidedAt', 'decidedBy',
            'requesterId', 'requesterName', 'requesterAvatar',
        ]
        read_only_fields = ['votes', 'decided_at', 'decided_by']

    def get_requesterName(self, obj):
        name = f"{obj.requester.first_name} {obj.requester.last_name}".strip()
        return name if name else obj.requester.email.split('@')[0]

    def get_requesterAvatar(self, obj):
        return obj.requester.avatar or obj.requester.first_name[:2].upper()


class RecordSerializer(serializers.ModelSerializer):
    memberName = serializers.SerializerMethodField()
    memberId = serializers.CharField(source='member.id', read_only=True)

    class Meta:
        model = Record
        fields = ['id', 'group', 'amount', 'method', 'note', 'receipt_url', 'date', 'memberId', 'memberName']

    def get_memberName(self, obj):
        name = f"{obj.member.first_name} {obj.member.last_name}".strip()
        return name if name else obj.member.email.split('@')[0]


class LoanSerializer(serializers.ModelSerializer):
    requesterName = serializers.SerializerMethodField()
    requesterId = serializers.CharField(source='requester.id', read_only=True)
    groupId = serializers.CharField(source='group.id', read_only=True)
    interestRate = serializers.DecimalField(source='interest_rate', max_digits=5, decimal_places=2)
    startDate = serializers.CharField(source='start_date', required=False, allow_blank=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    decidedAt = serializers.DateTimeField(source='decided_at', read_only=True)
    decidedBy = serializers.CharField(source='decided_by', read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'group', 'groupId', 'title', 'amount', 'interestRate',
            'type', 'installments', 'frequency', 'startDate', 'reason',
            'repaid', 'status', 'createdAt', 'decidedAt', 'decidedBy',
            'requesterId', 'requesterName',
        ]
        read_only_fields = ['status', 'repaid', 'decided_at', 'decided_by']

    def get_requesterName(self, obj):
        name = f"{obj.requester.first_name} {obj.requester.last_name}".strip()
        return name if name else obj.requester.email.split('@')[0]


class GoalSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source='user.id', read_only=True)
    requesterName = serializers.SerializerMethodField()
    linkedGroupId = serializers.SerializerMethodField()
    targetAmount = serializers.DecimalField(source='target_amount', max_digits=12, decimal_places=2)
    savedAmount = serializers.DecimalField(source='saved_amount', max_digits=12, decimal_places=2, required=False)
    targetDate = serializers.DateField(source='target_date')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    decidedAt = serializers.DateTimeField(source='decided_at', read_only=True)
    decidedBy = serializers.CharField(source='decided_by', read_only=True)

    class Meta:
        model = Goal
        fields = [
            'id', 'userId', 'requesterName', 'linked_group', 'linkedGroupId',
            'title', 'targetAmount', 'savedAmount', 'targetDate',
            'notes', 'status', 'createdAt', 'decidedAt', 'decidedBy',
        ]
        read_only_fields = ['status', 'decided_at', 'decided_by']

    def get_requesterName(self, obj):
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return name if name else obj.user.email.split('@')[0]

    def get_linkedGroupId(self, obj):
        return obj.linked_group.id if obj.linked_group else ''
