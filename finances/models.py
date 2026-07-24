from django.db import models
from django.conf import settings
from groups.models import Group


class Request(models.Model):
    """Contribution and investment requests submitted by members."""
    REQUEST_TYPES = [
        ('loan', 'Loan'),
        ('investment', 'Investment'),
        ('contribution', 'Contribution'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('pending_secretary', 'Pending Secretary'),
        ('pending_treasury', 'Pending Treasury'),
        ('pending_audit', 'Pending Audit'),
        ('pending_chair', 'Pending Chair'),
        ('proposed', 'Proposed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),
    ]

    id = models.CharField(max_length=50, primary_key=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='requests')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requests')
    type = models.CharField(max_length=50, choices=REQUEST_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    title = models.CharField(max_length=255, blank=True)  # note / description
    method = models.CharField(max_length=100, blank=True)  # payment method
    note = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

    receipt_url = models.URLField(max_length=500, blank=True)
    votes = models.JSONField(default=dict, blank=True)  # {'yes': [user_ids], 'no': [user_ids]}

    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} - {self.amount} by {self.requester.email}"


class Record(models.Model):
    """Official contribution records created by admins or auto-generated on approval."""
    id = models.CharField(max_length=50, primary_key=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='records')
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='records')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=100, default='Unknown')
    note = models.TextField(blank=True)
    receipt_url = models.URLField(max_length=500, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Record: {self.amount} by {self.member.email}"


class Loan(models.Model):
    """Loan requests submitted by members, tracked separately from contribution requests."""
    LOAN_TYPES = [
        ('Flat Rate', 'Flat Rate'),
        ('Reducing Balance', 'Reducing Balance'),
    ]
    FREQ_CHOICES = [
        ('Weekly', 'Weekly'),
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
    ]
    STATUS_CHOICES = [
        ('pending_secretary', 'Pending Secretary'),
        ('pending_treasury', 'Pending Treasury'),
        ('pending_audit', 'Pending Audit'),
        ('pending_chair', 'Pending Chair'),
        ('pending_signature', 'Pending Signature'),
        ('pending_disbursal', 'Pending Disbursal'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('repaid', 'Repaid'),
    ]

    id = models.CharField(max_length=50, primary_key=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='loans')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loans')

    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    type = models.CharField(max_length=50, choices=LOAN_TYPES, default='Flat Rate')
    installments = models.IntegerField(default=1)
    frequency = models.CharField(max_length=20, choices=FREQ_CHOICES, default='Monthly')
    start_date = models.CharField(max_length=100, blank=True)
    reason = models.TextField(blank=True)
    repaid = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_secretary')
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Loan: {self.title} - {self.amount} by {self.requester.email}"


class Goal(models.Model):
    """Savings goals created by members, optionally linked to a group."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]

    id = models.CharField(max_length=50, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    linked_group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='goals'
    )

    title = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    saved_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target_date = models.DateField()
    notes = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Goal: {self.title} by {self.user.email}"
