from django.contrib.auth import get_user_model

from groups.models import Membership

User = get_user_model()

# Role-based action permissions.
ROLE_PERMISSIONS = {
    'sysadmin': {'create_group', 'onboard_members', 'manage_users', 'manage_groups'},
    'chair': {'create_group', 'onboard_members', 'manage_groups'},
    'mobilizer': {'create_group', 'onboard_members'},
    'treasury': set(),
    'secretary': set(),
    'audit': set(),
    'member': set(),
}


def has_permission(user, action: str) -> bool:
    """Return whether a given user role is allowed to perform an action."""
    if not user or not user.is_authenticated:
        return False

    if user.role == 'sysadmin':
        return True

    allowed_actions = ROLE_PERMISSIONS.get(user.role, set())
    return action in allowed_actions


def can_manage_group(user, group) -> bool:
    """Return True when the user can manage the given group."""
    if not user or not user.is_authenticated:
        return False

    if user.role == 'sysadmin':
        return True

    if user.role == 'chair':
        return True

    return Membership.objects.filter(user=user, group=group, role='admin').exists()
