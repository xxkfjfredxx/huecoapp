from rest_framework.routers import DefaultRouter
from .views import HuecoViewSet, ConfirmacionViewSet, ComentarioViewSet, PuntosUsuarioViewSet

router = DefaultRouter()
router.register(r'huecos', HuecoViewSet, basename='hueco')
router.register(r'confirmaciones', ConfirmacionViewSet, basename='confirmacion')
router.register(r'comentarios', ComentarioViewSet, basename='comentario')
router.register(r'puntos', PuntosUsuarioViewSet, basename='puntos')

urlpatterns = router.urls
