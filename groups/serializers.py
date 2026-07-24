from rest_framework import serializers
from .models import Group, Membership
from users.serializers import UserSerializer
from finances.serializers import RecordSerializer, RequestSerializer


class MembershipSerializer(serializers.ModelSerializer):
    # Flatten key user fields so frontend can access m.name, m.email, m.avatar, m.id directly
    id = serializers.IntegerField(source='user.id', read_only=True)
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    avatar = serializers.CharField(source='user.avatar', read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'name', 'email', 'avatar', 'role', 'joined_at']

    def get_name(self, obj):
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return name if name else obj.user.email.split('@')[0]


class GroupSerializer(serializers.ModelSerializer):
    members = MembershipSerializer(source='memberships', many=True, read_only=True)
    records = RecordSerializer(many=True, read_only=True)
    requests = RequestSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'contribution', 'frequency',
            'cycle', 'invite_code', 'rules', 'members', 'records', 'requests',
            'created_at',
        ]
