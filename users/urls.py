from django.urls import path
from .views import CurrentUserView, AdminCreateUserView, ChangePasswordView, UserListView, UserManageView

urlpatterns = [
    path('', UserListView.as_view(), name='user-list'),
    path('<int:user_id>/', UserManageView.as_view(), name='user-manage'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('create/', AdminCreateUserView.as_view(), name='admin-create-user'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
