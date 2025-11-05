from rest_framework.routers import DefaultRouter
from django.urls import path

# Importa tus ViewSets y la función summary
from apps.usuarios.api.v1.views import UserViewSet

router = DefaultRouter()

router.register(r"users", UserViewSet)
urlpatterns = [

] + router.urls
