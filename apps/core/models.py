from django.db import models

STATUS_CHOICES = [
    (0, 'Inactivo'),
    (1, 'Activo'),
]

class BaseStatusModel(models.Model):
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)

    class Meta:
        abstract = True
