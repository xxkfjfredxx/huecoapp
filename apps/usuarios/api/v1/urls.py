from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet
from .views_auth import LoginView, LogoutView, MeView

router = DefaultRouter()
router.register(r"users", UserViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]
