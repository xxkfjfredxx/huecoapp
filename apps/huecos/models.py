# apps/huecos/models.py
from django.db import models
from apps.core.models import BaseStatusModel
from django.conf import settings
from apps.utils.mixins import AuditMixin
from apps.usuarios.models import User

class EstadoHueco(models.IntegerChoices):
    PENDIENTE = 1, 'Pendiente de validación'
    ACTIVO = 2, 'Activo'
    RECHAZADO = 3, 'Rechazado'
    REABIERTO = 4, 'Reabierto'
    CERRADO = 5, 'Cerrado'
    EN_REPARACION = 6, 'En reparación'
    REPARADO = 7, 'Reparado'

class Hueco(AuditMixin, BaseStatusModel):
    # Usamos los choices numéricos
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    usuario = models.ForeignKey('usuarios.User', on_delete=models.CASCADE, related_name='huecos')
    latitud = models.FloatField()
    longitud = models.FloatField()
    descripcion = models.TextField(blank=True, null=True)
    
    estado = models.PositiveSmallIntegerField(
        choices=EstadoHueco.choices, 
        default=EstadoHueco.PENDIENTE
    )
    
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    numero_ciclos = models.IntegerField(default=0)
    validaciones_positivas = models.IntegerField(default=0)
    validaciones_negativas = models.IntegerField(default=0)
    imagen = models.ImageField(upload_to="huecos/", null=True, blank=True)
    imagen_preview = models.ImageField(upload_to="huecos/preview/", null=True, blank=True)
    denuncias_count = models.PositiveIntegerField(default=0)

    # Nuevos campos
    vistas = models.IntegerField(default=0)
    GRAVEDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
    ]
    gravedad = models.CharField(max_length=10, choices=GRAVEDAD_CHOICES, default='media')

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # 2. Procesamiento de Imagen: Delegar a Celery
        if is_new and self.imagen:
            from django.db import transaction
            from apps.huecos.tasks import optimizar_imagen_hueco_task
            
            def safe_delay():
                try:
                    optimizar_imagen_hueco_task.delay(self.pk)
                except Exception as e:
                    print(f"Error al encolar tarea de optimización (post-commit): {e}")

            transaction.on_commit(safe_delay)
            
    def evaluar_validaciones(self):
        from apps.huecos.services.puntos_service import evaluar_validaciones_hueco
        evaluar_validaciones_hueco(self)


    def __str__(self):
        return f"Hueco #{self.id} ({self.estado})"


class HistorialHueco(AuditMixin):
    hueco = models.ForeignKey(Hueco, on_delete=models.CASCADE, related_name="historial")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    accion = models.CharField(max_length=100)  # ej: "creado", "marcado como reparado", "confirmado"
    fecha = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(blank=True)

    def __str__(self):
        return f"{self.accion} por {self.usuario} en {self.fecha}"


class Confirmacion(AuditMixin, BaseStatusModel):
    hueco = models.ForeignKey(Hueco, on_delete=models.CASCADE, related_name="confirmaciones")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nuevo_estado = models.PositiveSmallIntegerField(choices=EstadoHueco.choices, default=EstadoHueco.PENDIENTE) 
    numero_ciclo = models.IntegerField(default=0)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("hueco", "usuario", "numero_ciclo")

    def __str__(self):
        return f"{self.usuario} confirmó hueco {self.hueco.id} ciclo {self.numero_ciclo}"


class Comentario(AuditMixin, BaseStatusModel):
    hueco = models.ForeignKey(Hueco, on_delete=models.CASCADE, related_name="comentarios")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    texto = models.TextField()
    imagen = models.ImageField(upload_to="comentarios/", null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comentario de {self.usuario} en Hueco {self.hueco.id}"


class PuntosUsuario(AuditMixin):
    TIPOS = [
        ("reporte", "Reporte creado"),
        ("verificacion", "Reporte verificado"),
        ("confirmacion", "Confirmación de estado"),
        ("comentario", "Comentario o interacción"),
        ("reporte_falso", "Reporte falso o rechazado"),
        ("admin", "Ajuste manual"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="historial_puntos"
    )
    tipo = models.CharField(max_length=50, choices=TIPOS)
    puntos = models.IntegerField(default=0)
    descripcion = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        signo = "+" if self.puntos >= 0 else ""
        return f"{self.usuario} {signo}{self.puntos} pts ({self.tipo})"

    def save(self, *args, **kwargs):
        """
        Guarda el registro y actualiza automáticamente la reputación del usuario.
        Si es un reporte falso o penalización, resta puntos.
        """
        super().save(*args, **kwargs)

        from apps.usuarios.models import ReputacionUsuario  # evitar import circular
        reputacion, _ = ReputacionUsuario.objects.get_or_create(usuario=self.usuario)

        # 🔹 Actualiza puntaje
        reputacion.puntaje_total += self.puntos
        reputacion.actualizar_nivel()  # actualiza automáticamente el nivel de confianza
        reputacion.save()

        # 🔸 Reglas especiales
        # Si el usuario recibe una penalización fuerte, puedes degradarlo
        if reputacion.puntaje_total < 0:
            reputacion.nivel_confianza = "nuevo"
            reputacion.save()


class ValidacionHueco(AuditMixin, BaseStatusModel):
    hueco = models.ForeignKey(Hueco, on_delete=models.CASCADE, related_name="validaciones")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    voto = models.BooleanField(help_text="True = confirma que el hueco existe, False = no existe")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('hueco', 'usuario')

    def __str__(self):
        return f"Validación de {self.usuario} sobre hueco #{self.hueco.id}"
    

class DispositivoUsuario(BaseStatusModel):
    """
    Guarda el token FCM de cada dispositivo móvil.
    Un usuario puede tener varios dispositivos.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dispositivos"
    )
    token_fcm = models.CharField(max_length=255, unique=True)
    plataforma = models.CharField(max_length=20, default="android")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.plataforma}"


class Suscripcion(AuditMixin, BaseStatusModel):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suscripciones'
    )
    hueco = models.ForeignKey(
        'Hueco',  # referencia en string porque Hueco está en el mismo archivo
        on_delete=models.CASCADE,
        related_name='suscripciones'
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'hueco')

    def __str__(self):
        return f"{self.usuario} sigue hueco {self.hueco_id}"

class DenunciaHueco(AuditMixin, BaseStatusModel):
    MOTIVOS = [
        ('obscene', 'Imagen Obscena/Inapropiada'),
        ('spam', 'Spam / Falso'),
        ('offensive', 'Lenguaje Ofensivo'),
        ('other', 'Otro'),
    ]
    
    hueco = models.ForeignKey(Hueco, on_delete=models.CASCADE, related_name='denuncias')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    motivo = models.CharField(max_length=20, choices=MOTIVOS, default='other')
    comentario = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('hueco', 'usuario')

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Incrementar contador en el hueco
            self.hueco.denuncias_count += 1
            if self.hueco.denuncias_count >= 3:
                # Ocultar automáticamente
                self.hueco.status = 0
                self.hueco.is_deleted = True
            self.hueco.save(update_fields=['denuncias_count', 'status', 'is_deleted'])

    def __str__(self):
        return f"Denuncia de {self.usuario} a Hueco #{self.hueco.id}"