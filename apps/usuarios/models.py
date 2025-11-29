import hashlib
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.validators import UnicodeUsernameValidator
from apps.utils.mixins import AuditMixin
from apps.core.models import BaseStatusModel
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AuditMixin, BaseStatusModel, AbstractUser):
    email = models.EmailField(_('email address'), max_length=254, unique=True)
    token_version = models.PositiveIntegerField(default=1)
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=False,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[UnicodeUsernameValidator()],
        error_messages={'unique': _("A user with that username already exists.")},
    )
    AUTH_PROVIDERS = (
        ("email", "Email/Password"),
        ("google", "Google"),
        ("facebook", "Facebook"),
        ("mixed", "Google + Email"), 
    )
    auth_provider = models.CharField(max_length=20, choices=AUTH_PROVIDERS, default="email")
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = "users"

    def soft_delete(self, user=None):
        if not self.is_deleted:
            self.is_deleted = True
            self.is_active = False
            self.save()


class ReputacionUsuario(models.Model):
    """
    Mide la confiabilidad del usuario basada en su actividad y puntos ganados.
    """
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="reputacion")
    puntaje_total = models.IntegerField(default=0)
    nivel_confianza = models.CharField(max_length=20, default="nuevo")  # nuevo, confiable, experto

    def actualizar_nivel(self):
        """Actualiza el nivel de confianza según el puntaje acumulado."""
        if self.puntaje_total >= 200:
            self.nivel_confianza = "experto"
        elif self.puntaje_total >= 100:
            self.nivel_confianza = "confiable"
        else:
            self.nivel_confianza = "nuevo"

    def save(self, *args, **kwargs):
        # Antes de guardar, actualiza automáticamente el nivel
        self.actualizar_nivel()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} ({self.nivel_confianza})"


@receiver(post_save, sender=User)
def crear_reputacion_usuario(sender, instance, created, **kwargs):
    """Crea automáticamente una reputación al crear un nuevo usuario."""
    if created:
        ReputacionUsuario.objects.create(usuario=instance)


class LoginOTP(models.Model):
    """
    Sistema de inicio de sesión sin contraseña mediante códigos OTP.
    """
    user = models.ForeignKey("usuarios.User", on_delete=models.CASCADE, related_name="login_otps")
    code_hash = models.CharField(max_length=128, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)

    class Meta:
        db_table = "user_login_otps"
        indexes = [models.Index(fields=["expires_at"])]

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
