from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from groups.views import GroupViewSet
from finances.views import RequestViewSet, RecordViewSet, LoanViewSet, GoalViewSet

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'requests', RequestViewSet, basename='request')
router.register(r'records', RecordViewSet, basename='record')
router.register(r'loans', LoanViewSet, basename='loan')
router.register(r'goals', GoalViewSet, basename='goal')


def health_check(request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/users/', include('users.urls')),
    path('api/', include(router.urls)),
]
