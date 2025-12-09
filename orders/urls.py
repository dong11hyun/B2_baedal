from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderV1ViewSet

router = DefaultRouter()
router.register(r'orders', OrderV1ViewSet)

urlpatterns = [
    path('v1/', include(router.urls)),
]