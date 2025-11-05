# config/urls_v1.py
from rest_framework.routers import DefaultRouter
from django.urls import path

# Importa tus ViewSets y la función summary
from apps.usuarios.api.v1.views import UserViewSet
from apps.huecos.views import HuecoViewSet, ConfirmacionViewSet, ComentarioViewSet, PuntosUsuarioViewSet,ValidacionHuecoViewSet,HuecosCercanosViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r'huecos', HuecoViewSet, basename='hueco')
router.register(r'huecos/cercanos', HuecosCercanosViewSet, basename='huecos-cercanos')
router.register(r"validaciones", ValidacionHuecoViewSet)
router.register(r'confirmaciones', ConfirmacionViewSet, basename='confirmacion')
router.register(r'comentarios', ComentarioViewSet, basename='comentario')
router.register(r'puntos', PuntosUsuarioViewSet, basename='puntos')
# 2) Insertamos summary ANTES de router.urls
urlpatterns = [
    
] + router.urls
