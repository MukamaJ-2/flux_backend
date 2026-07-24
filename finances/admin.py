from django.contrib import admin
from .models import Request, Record, Loan, Goal


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'amount', 'requester', 'group', 'status', 'created_at')
    list_filter = ('type', 'status', 'group')
    search_fields = ('requester__email', 'title')


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'member', 'group', 'method', 'date')
    list_filter = ('group', 'method')
    search_fields = ('member__email', 'note')


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'amount', 'requester', 'group', 'status', 'created_at')
    list_filter = ('status', 'group', 'type')
    search_fields = ('requester__email', 'title', 'reason')


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'target_amount', 'saved_amount', 'user', 'status', 'target_date')
    list_filter = ('status', 'linked_group')
    search_fields = ('user__email', 'title')
