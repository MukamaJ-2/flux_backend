from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions


class ActiveJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User account is disabled.', code='user_inactive')
        return user
