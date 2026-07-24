from django.contrib import admin
from .models import Group, Membership

class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'contribution', 'frequency', 'cycle')
    search_fields = ('name', 'id')
    inlines = [MembershipInline]

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'joined_at')
    list_filter = ('group', 'role')
    search_fields = ('user__email', 'group__name')
