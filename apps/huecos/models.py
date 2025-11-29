# apps/huecos/models.py
from django.db import models
from apps.core.models import BaseStatusModel
from django.conf import settings
from apps.utils.mixins import AuditMixin
from apps.usuarios.models import User

class Hueco(AuditMixin, BaseStatusModel):
    ESTADOS = [
        ('pendiente_validacion', 'Pendiente de validación'),
        ('activo', 'Activo'),
        ('rechazado', 'Rechazado'),
        ('reabierto', 'Reabierto'),
        ('cerrado', 'Cerrado'),
    ]
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    usuario = models.ForeignKey('usuarios.User', on_delete=models.CASCADE, related_name='huecos')
    latitud = models.FloatField()
    longitud = models.FloatField()
    descripcion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=30, choices=ESTADOS, default='pendiente_validacion')
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    numero_ciclos = models.IntegerField(default=0)
    validaciones_positivas = models.IntegerField(default=0)
    validaciones_negativas = models.IntegerField(default=0)
    imagen = models.ImageField(upload_to="huecos/", null=True, blank=True)

    def evaluar_validaciones(self):
        """
        Evalúa si el hueco debe pasar a 'activo' o 'rechazado' según las validaciones,
        aplicando votos ponderados por nivel de reputación:
          - nuevo: 1 punto
          - confiable: 1.5 puntos
          - experto: 2 puntos
        """
        positivas = 0
        negativas = 0

        for v in self.validaciones.all():
            reputacion = getattr(v.usuario.reputacion, 'nivel_confianza', 'nuevo')
            peso = 1
            if reputacion == 'confiable':
                peso = 1.5
            elif reputacion == 'experto':
                peso = 2

            if v.voto:
                positivas += peso
            else:
                negativas += peso

        self.validaciones_positivas = positivas
        self.validaciones_negativas = negativas

        # 🔹 Umbrales (ponderados)
        if positivas >= 5 and self.estado == 'pendiente_validacion':
            self.estado = 'activo'
            self.save()
            self.asignar_puntos_aprobacion()

        elif negativas >= 3 and self.estado == 'pendiente_validacion':
            self.estado = 'rechazado'
            self.save()
            self.asignar_puntos_rechazo()

    def asignar_puntos_aprobacion(self):
        from apps.huecos.services.puntos_service import registrar_puntos
        # 🔹 El creador gana más puntos
        registrar_puntos(self.usuario, 10, "validacion", "Validación positiva de hueco")

        # 🔹 Los validadores positivos también ganan puntos
        for validacion in self.validaciones.filter(voto=True):
            if validacion.usuario != self.usuario:
                registrar_puntos(validacion.usuario, 5, "confirmacion", f"Validación positiva del hueco")

    def asignar_puntos_rechazo(self):
        from apps.huecos.services.puntos_service import registrar_puntos
        # 🔸 Penaliza al creador
        registrar_puntos(self.usuario, -15, "reporte_falso", f"Hueco #{self.id} rechazado como reporte falso")

        # 🔹 Recompensa a los que votaron correctamente en contra
        for validacion in self.validaciones.filter(voto=False):
            if validacion.usuario != self.usuario:
                registrar_puntos(validacion.usuario, 3, "verificacion", f"Validación correcta: Hueco #{self.id} era falso")


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
    confirmado = models.BooleanField()  # True = sigue, False = reparado
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("hueco", "usuario")

    def __str__(self):
        return f"{self.usuario} confirmó hueco {self.hueco.id}"


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