from rest_framework import serializers
from .models import Hueco, HistorialHueco, Confirmacion, Comentario, PuntosUsuario, ValidacionHueco,Suscripcion


class ComentarioSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = Comentario
        fields = ['id', 'usuario', 'usuario_nombre', 'texto', 'imagen', 'fecha']


class HuecoSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)
    comentarios = ComentarioSerializer(many=True, read_only=True)
    confirmaciones_count = serializers.IntegerField(source='confirmaciones.count', read_only=True)
    distancia_m = serializers.FloatField(read_only=True)

    class Meta:
        model = Hueco
        fields = [
            'id',
            'usuario',
            'usuario_nombre',
            'ciudad',
            'descripcion',
            'latitud',
            'longitud',
            'estado',
            'fecha_reporte',
            'fecha_actualizacion',
            'numero_ciclos',
            'validaciones_positivas',
            'validaciones_negativas',
            'imagen',
            'comentarios',
            'confirmaciones_count',
            'distancia_m',
        ]

class ConfirmacionSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = Confirmacion
        fields = ['id', 'hueco', 'usuario', 'usuario_nombre', 'confirmado', 'fecha']


class HistorialHuecoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialHueco
        fields = '__all__'


class PuntosUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuntosUsuario
        fields = '__all__'


class ValidacionHuecoSerializer(serializers.ModelSerializer):
    hueco_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ValidacionHueco
        fields = ['id', 'hueco', 'hueco_detalle', 'voto', 'usuario', 'fecha']
        read_only_fields = ['usuario', 'fecha', 'hueco_detalle']

    def get_hueco_detalle(self, obj):
        """Devuelve información resumida del hueco."""
        return {
            "id": obj.hueco.id,
            "estado": obj.hueco.estado,
            "descripcion": obj.hueco.descripcion,
            "latitud": obj.hueco.latitud,
            "longitud": obj.hueco.longitud,
        }

    def validate(self, data):
        """
        Evita que el usuario valide más de una vez el mismo hueco.
        """
        request = self.context.get('request')
        user = request.user if request else None

        if user and ValidacionHueco.objects.filter(hueco=data['hueco'], usuario=user).exists():
            raise serializers.ValidationError("Ya has validado este hueco.")
        return data


class SuscripcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suscripcion
        fields = ['id', 'usuario', 'hueco', 'fecha', 'status']
