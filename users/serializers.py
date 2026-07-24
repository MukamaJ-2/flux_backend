from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    fullName = serializers.SerializerMethodField()
    isAdmin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'fullName', 'phone', 'role', 'avatar', 'isAdmin',
            'is_active',
            'must_change_password',
        ]
        read_only_fields = ['id', 'email', 'username']

    def get_fullName(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.email.split('@')[0]

    def get_isAdmin(self, obj):
        return obj.role in ('sysadmin', 'chair')
