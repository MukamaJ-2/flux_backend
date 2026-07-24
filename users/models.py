from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    ROLE_CHOICES = [
        ('sysadmin', 'Sysadmin'),
        ('chair', 'Chair'),
        ('treasury', 'Treasury'),
        ('secretary', 'Secretary'),
        ('audit', 'Audit'),
        ('mobilizer', 'Mobilizer'),
        ('member', 'Member'),
    ]

    email = models.EmailField(_("email address"), unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    avatar = models.CharField(max_length=10, blank=True, help_text="Initials or short text avatar")
    must_change_password = models.BooleanField(
        default=False,
        help_text="Force user to set a new password on next login"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
