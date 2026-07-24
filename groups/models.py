from django.db import models
from django.conf import settings
from django.utils.crypto import get_random_string


def _gen_invite_code():
    """Generate a unique 8-character uppercase alphanumeric invite code."""
    return get_random_string(8, allowed_chars='ABCDEFGHJKLMNPQRSTUVWXYZ23456789')


class Group(models.Model):
    id = models.CharField(max_length=50, primary_key=True) # e.g. "flux-main"
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    contribution = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=50, default='Monthly')
    cycle = models.CharField(max_length=50, default='OPEN')
    invite_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    rules = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-generate a unique invite code on creation
        if not self.invite_code:
            code = _gen_invite_code()
            while Group.objects.filter(invite_code=code).exists():
                code = _gen_invite_code()
            self.invite_code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=50, default='member') # "admin" or "member" within group
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.email} in {self.group.name}"
