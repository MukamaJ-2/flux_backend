from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import datetime
from .serializers import UserSerializer

User = get_user_model()


def _generate_default_password():
    """Generate a default password like Flux@Jun2026!"""
    month = datetime.now().strftime('%b')
    year = datetime.now().strftime('%Y')
    return f"Flux@{month}{year}!"


class AdminCreateUserView(APIView):
    """
    POST /api/users/create/
    Sysadmin-only: Create a new user with a default password.
    The new user will be forced to change their password on first login.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'sysadmin':
            return Response(
                {'error': 'Only sysadmins can create new users.'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data
        full_name = data.get('fullName', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        role = data.get('role', 'member').strip()

        if not email or not full_name:
            return Response(
                {'error': 'Full name and email are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not email.endswith('@gmail.com'):
            return Response(
                {'error': 'Only Gmail accounts are allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'A user with this email already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        allowed_roles = ['sysadmin', 'chair', 'treasury', 'secretary', 'audit', 'mobilizer', 'member']
        if role not in allowed_roles:
            return Response(
                {'error': f'Invalid role. Choose from: {", ".join(allowed_roles)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Split full name
        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        # Generate unique username from email
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        default_password = _generate_default_password()

        user = User.objects.create_user(
            username=username,
            email=email,
            password=default_password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
            avatar=full_name[:2].upper() if full_name else email[:2].upper(),
            must_change_password=True,
        )

        serializer = UserSerializer(user)
        return Response(
            {
                **serializer.data,
                'default_password': default_password,  # Shown to admin to share with member
            },
            status=status.HTTP_201_CREATED
        )


class ChangePasswordView(APIView):
    """
    POST /api/users/change-password/
    Authenticated: User sets a new password (clears must_change_password flag).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        new_password = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')

        if not new_password or not confirm_password:
            return Response(
                {'error': 'Both new_password and confirm_password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return Response(
                {'error': 'Passwords do not match.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        user.set_password(new_password)
        user.must_change_password = False
        user.save()

        return Response({'success': True, 'message': 'Password updated successfully.'})


class CurrentUserView(APIView):
    """
    GET  /api/users/me/  — Fetch current user profile
    PATCH /api/users/me/ — Update own profile (name, phone, avatar)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        user = request.user
        data = request.data

        if 'fullName' in data:
            parts = data['fullName'].strip().split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''

        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'avatar' in data:
            user.avatar = data['avatar']
        if 'role' in data:
            if request.user.role != 'sysadmin':
                return Response(
                    {'error': 'Only sysadmins can change roles.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            allowed_roles = ['sysadmin', 'chair', 'treasury', 'secretary', 'audit', 'mobilizer', 'member']
            new_role = data['role']
            if new_role not in allowed_roles:
                return Response(
                    {'error': f'Invalid role. Choose from: {", ".join(allowed_roles)}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if user.role == 'sysadmin' and new_role != 'sysadmin':
                sysadmin_count = User.objects.filter(role='sysadmin').count()
                if sysadmin_count <= 1:
                    return Response(
                        {'error': 'Cannot remove the last sysadmin role.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            user.role = new_role

        user.save()
        serializer = UserSerializer(user)
        return Response(serializer.data)


class UserListView(APIView):
    """
    GET /api/users/ — Fetch all users (Sysadmin only)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'sysadmin':
            return Response({'error': 'Only sysadmins can view all users.'}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.all().order_by('-date_joined')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class UserManageView(APIView):
    """
    PATCH /api/users/<id>/ — Update a user's role/profile fields (sysadmin only)
    DELETE /api/users/<id>/ — Delete a user (sysadmin only)
    """
    permission_classes = [IsAuthenticated]

    def _ensure_sysadmin(self, request):
        if request.user.role != 'sysadmin':
            return Response({'error': 'Only sysadmins can manage users.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def _get_target_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def patch(self, request, user_id):
        forbidden = self._ensure_sysadmin(request)
        if forbidden:
            return forbidden

        target_user = self._get_target_user(user_id)
        if not target_user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data

        if 'role' in data:
            allowed_roles = ['sysadmin', 'chair', 'treasury', 'secretary', 'audit', 'mobilizer', 'member']
            new_role = str(data['role']).strip()
            if new_role not in allowed_roles:
                return Response(
                    {'error': f'Invalid role. Choose from: {", ".join(allowed_roles)}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if target_user.role == 'sysadmin' and new_role != 'sysadmin':
                sysadmin_count = User.objects.filter(role='sysadmin').count()
                if sysadmin_count <= 1:
                    return Response(
                        {'error': 'Cannot remove the last sysadmin role.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            target_user.role = new_role

        if 'is_active' in data:
            if target_user.id == request.user.id:
                return Response(
                    {'error': 'You cannot change your own active status.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            is_active_value = data['is_active']
            if isinstance(is_active_value, str):
                is_active_value = is_active_value.lower() in ('true', '1', 'yes')
            if target_user.role == 'sysadmin' and not bool(is_active_value):
                sysadmin_count = User.objects.filter(role='sysadmin', is_active=True).count()
                if sysadmin_count <= 1:
                    return Response(
                        {'error': 'Cannot deactivate the last active sysadmin account.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            target_user.is_active = bool(is_active_value)

        if 'fullName' in data:
            parts = str(data['fullName']).strip().split(' ', 1)
            target_user.first_name = parts[0]
            target_user.last_name = parts[1] if len(parts) > 1 else ''

        if 'phone' in data:
            target_user.phone = data['phone']

        if 'avatar' in data:
            target_user.avatar = data['avatar']

        target_user.save()
        serializer = UserSerializer(target_user)
        return Response(serializer.data)

    def delete(self, request, user_id):
        forbidden = self._ensure_sysadmin(request)
        if forbidden:
            return forbidden

        target_user = self._get_target_user(user_id)
        if not target_user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if target_user.id == request.user.id:
            return Response({'error': 'You cannot delete your own account.'}, status=status.HTTP_400_BAD_REQUEST)

        if target_user.role == 'sysadmin':
            sysadmin_count = User.objects.filter(role='sysadmin').count()
            if sysadmin_count <= 1:
                return Response(
                    {'error': 'Cannot delete the last sysadmin account.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        target_user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
