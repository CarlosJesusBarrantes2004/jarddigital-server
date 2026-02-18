from rest_framework import serializers
from django.utils import timezone
from .models import EstadoSOT, SubEstadoSOT, EstadoAudio, Producto, GrabadorAudio, Venta
from apps.users.models import SupervisorAsignacion, PermisoAcceso
from django.db import transaction
from apps.sales.models import HistorialAgendaSOT

# ==========================================
# 1. CATÁLOGOS Y ESTADOS (Fase 1)
# ==========================================

class EstadoSOTSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoSOT
        fields = ['id', 'codigo', 'nombre', 'orden', 'es_final', 'color_hex', 'activo']


class SubEstadoSOTSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubEstadoSOT
        fields = ['id', 'nombre', 'color_hex', 'requiere_nueva_fecha', 'activo']


class EstadoAudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoAudio
        fields = ['id', 'codigo', 'nombre', 'activo']


# ==========================================
# 2. OPERATIVOS Y PRODUCTOS (Fase 2)
# ==========================================

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = [
            'id',
            'nombre_plan',
            'es_alto_valor',
            'costo_fijo_plan',
            'comision_base',
            'fecha_inicio_vigencia',
            'fecha_fin_vigencia',
            'activo'
        ]


class GrabadorAudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrabadorAudio
        fields = ['id', 'id_usuario', 'nombre_completo', 'activo']


class VentaSerializer(serializers.ModelSerializer):
    # Campos visuales de solo lectura (Para que el frontend pinte las tablas bonitas)
    nombre_asesor = serializers.CharField(source='id_asesor.nombre_completo', read_only=True)
    nombre_producto = serializers.CharField(source='id_producto.nombre_plan', read_only=True)
    nombre_estado = serializers.CharField(source='id_estado_sot.nombre', read_only=True)
    nombre_supervisor = serializers.CharField(source='id_supervisor_vigente.id_supervisor.nombre_completo',
                                              read_only=True)

    class Meta:
        model = Venta
        fields = '__all__'

        # 1. BLOQUEO ABSOLUTO DE AUDITORÍA (Ni Asesor ni Backoffice los tocan manualmente)
        read_only_fields = [
            'id_asesor', 'id_origen_venta', 'id_supervisor_vigente',
            'usuario_creacion', 'fecha_creacion', 'usuario_modificacion', 'fecha_modificacion'
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        # ==========================================
        # 1. INYECCIÓN DEL CONTEXTO DEL ASESOR
        # ==========================================
        validated_data['id_asesor'] = user
        validated_data['usuario_creacion'] = user

        # Extraemos la Sede a la que pertenece el Asesor (Asumimos la primera activa que tenga)
        permiso_sede = PermisoAcceso.objects.filter(
            id_usuario=user,
            id_modalidad_sede__activo=True
        ).select_related('id_modalidad_sede').first()

        if not permiso_sede:
            raise serializers.ValidationError({"error": "No tienes ninguna Sede/Modalidad asignada. Contacta a RRHH."})

        modalidad_sede_actual = permiso_sede.id_modalidad_sede
        validated_data['id_origen_venta'] = modalidad_sede_actual

        # Extraemos al supervisor vigente de esa Sede
        supervisor_activo = SupervisorAsignacion.objects.filter(
            id_modalidad_sede=modalidad_sede_actual,
            fecha_fin__isnull=True,
            activo=True
        ).first()

        if not supervisor_activo:
            raise serializers.ValidationError(
                {"error": f"La sede {modalidad_sede_actual.id_sucursal.nombre} no tiene supervisor activo."})

        validated_data['id_supervisor_vigente'] = supervisor_activo

        # ==========================================
        # 2. LIMPIEZA FORZADA (El Asesor manda vacío, pero si manda algo, lo borramos)
        # ==========================================
        campos_backoffice = [
            'codigo_sec', 'codigo_sot', 'fecha_visita_programada', 'id_sub_estado_sot',
            'fecha_real_inst', 'fecha_rechazo', 'comentario_gestion',
            'fecha_revision_audios', 'usuario_revision_audios', 'observacion_audios'
        ]
        for campo in campos_backoffice:
            validated_data.pop(campo, None)  # Lo eliminamos del JSON si el Asesor intentó mandarlo

        # ==========================================
        # 3. ESTADOS POR DEFECTO Y LÓGICA DE AUDIOS
        # ==========================================
        # Asignamos el Estado SOT EJECUCION
        estado_sot_ejecucion = EstadoSOT.objects.filter(codigo='EJECUCION').first()
        if not estado_sot_ejecucion:
            raise serializers.ValidationError({"error": "Falta configurar el Estado SOT 'EJECUCION' en la BD."})
        validated_data['id_estado_sot'] = estado_sot_ejecucion

        # Asignamos el Estado Audio PENDIENTE
        estado_audio_pendiente = EstadoAudio.objects.filter(codigo='PENDIENTE').first()
        if not estado_audio_pendiente:
            raise serializers.ValidationError({"error": "Falta configurar el Estado Audio 'PENDIENTE' en la BD."})
        validated_data['id_estado_audios'] = estado_audio_pendiente

        # Lógica de audio: Si el Asesor mandó audios, marcamos true y ponemos la fecha
        if validated_data.get('audio_subido') is True:
            validated_data['fecha_subida_audios'] = timezone.now()
        else:
            validated_data['audio_subido'] = False
            validated_data['fecha_subida_audios'] = None

        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user

        # 1. AUDITORÍA BASE
        validated_data['usuario_modificacion'] = user

        # Extraemos variables clave para comparar el "Antes" y el "Después"
        nueva_fecha_visita = validated_data.get('fecha_visita_programada')
        nuevo_sub_estado = validated_data.get('id_sub_estado_sot')
        nuevo_estado_sot = validated_data.get('id_estado_sot')
        nuevo_estado_audio = validated_data.get('id_estado_audios')

        # Guardamos la fecha antigua en memoria antes de que se sobrescriba
        fecha_visita_antigua = instance.fecha_visita_programada

        with transaction.atomic():

            # ==========================================
            # 2. TRIGGER DE AUDIOS (Revisión de Backoffice)
            # ==========================================
            # Si el Backoffice está cambiando el estado del audio (ej. a CONFORME o RECHAZADO)
            if nuevo_estado_audio and nuevo_estado_audio != instance.id_estado_audios:
                validated_data['usuario_revision_audios'] = user
                validated_data['fecha_revision_audios'] = timezone.now()

            # ==========================================
            # 3. TRIGGER DE ESTADOS FINALES (SOT)
            # ==========================================
            if nuevo_estado_sot and nuevo_estado_sot != instance.id_estado_sot:
                # Si lo pasan a RECHAZADO y no mandaron fecha manual, la auto-completamos
                if nuevo_estado_sot.codigo == 'RECHAZADO' and not validated_data.get('fecha_rechazo'):
                    validated_data['fecha_rechazo'] = timezone.now()

                # Si lo pasan a ATENDIDO (Final) y no hay fecha real, la auto-completamos
                elif nuevo_estado_sot.es_final and nuevo_estado_sot.codigo != 'RECHAZADO' and not validated_data.get(
                        'fecha_real_inst'):
                    validated_data['fecha_real_inst'] = timezone.now()

            # ==========================================
            # 4. GUARDADO DE LA VENTA
            # ==========================================
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()

            # ==========================================
            # 5. TRIGGER DEL HISTORIAL DE AGENDA
            # ==========================================
            # Si detectamos que la fecha programada cambió respecto a lo que había en BD
            if nueva_fecha_visita and nueva_fecha_visita != fecha_visita_antigua:

                # Solo creamos historial si hay un motivo (SubEstado) válido para el cambio
                if nuevo_sub_estado and nuevo_sub_estado.requiere_nueva_fecha:
                    HistorialAgendaSOT.objects.create(
                        id_venta=instance,
                        fecha_anterior=fecha_visita_antigua,  # Puede ser nula la primera vez
                        fecha_nueva=nueva_fecha_visita,
                        id_sub_estado_motivo=nuevo_sub_estado,
                        usuario_responsable=user
                    )

        return instance