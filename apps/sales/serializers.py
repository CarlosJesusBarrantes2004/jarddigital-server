from rest_framework import serializers
from django.utils import timezone
from django.db.models import Q
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

        # 1. BLOQUEO ABSOLUTO DE AUDITORÍA
        read_only_fields = [
            'id_asesor', 'id_origen_venta', 'id_supervisor_vigente',
            'usuario_creacion', 'fecha_creacion', 'usuario_modificacion', 'fecha_modificacion'
        ]

        # 2. VALIDACIONES ESTRICTAS (REGLAS DE NEGOCIO)
        extra_kwargs = {
            # Relajamos estos porque los llena el sistema o el Backoffice
            'id_estado_sot': {'required': False},
            'id_estado_audios': {'required': False},

            # ¡OBLIGATORIOS PARA EL ASESOR!
            'cliente_email': {'required': True, 'allow_null': False},
            'coordenadas_gps': {'required': True, 'allow_null': False},
            'score_crediticio': {'required': True, 'allow_null': False},
            'id_grabador_audios': {'required': True, 'allow_null': False}
        }

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        # ==========================================
        # 1. INYECCIÓN DEL CONTEXTO DEL ASESOR
        # ==========================================
        validated_data['id_asesor'] = user
        validated_data['usuario_creacion'] = user

        # Extraemos la Sede a la que pertenece el Asesor
        permiso_sede = PermisoAcceso.objects.filter(
            id_usuario=user,
            id_modalidad_sede__activo=True
        ).select_related('id_modalidad_sede').first()

        if not permiso_sede:
            raise serializers.ValidationError({"error": "No tienes ninguna Sede/Modalidad asignada. Contacta a RRHH."})

        modalidad_sede_actual = permiso_sede.id_modalidad_sede
        validated_data['id_origen_venta'] = modalidad_sede_actual

        # Buscamos al jefe (vigente hoy o indefinido)
        hoy = timezone.now().date()
        supervisor_activo = SupervisorAsignacion.objects.filter(
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy),
            id_modalidad_sede=modalidad_sede_actual,
            activo=True
        ).first()

        if not supervisor_activo:
            raise serializers.ValidationError({
                                                  "error": f"La sede {modalidad_sede_actual.id_sucursal.nombre} no tiene supervisor activo para el día de hoy."})

        validated_data['id_supervisor_vigente'] = supervisor_activo

        # ==========================================
        # 2. LIMPIEZA FORZADA (Campos prohibidos para el Asesor)
        # ==========================================
        campos_backoffice = [
            'codigo_sec', 'codigo_sot', 'fecha_visita_programada', 'bloque_horario', 'id_sub_estado_sot',
            'fecha_real_inst', 'fecha_rechazo', 'comentario_gestion',
            'fecha_revision_audios', 'usuario_revision_audios', 'observacion_audios',
            'audio_subido'  # Agregado aquí para que el Asesor no lo toque
        ]
        for campo in campos_backoffice:
            validated_data.pop(campo, None)

            # ==========================================
        # 3. ESTADOS POR DEFECTO
        # ==========================================
        # Asignamos el Estado SOT 'EJECUCION' (Pedido por tu compañero)
        estado_sot_ejecucion = EstadoSOT.objects.filter(codigo='EJECUCION').first()
        if not estado_sot_ejecucion:
            raise serializers.ValidationError({"error": "Falta configurar el Estado SOT 'EJECUCION' en la BD."})
        validated_data['id_estado_sot'] = estado_sot_ejecucion

        # Asignamos el Estado Audio 'PENDIENTE'
        estado_audio_pendiente = EstadoAudio.objects.filter(codigo='PENDIENTE').first()
        if not estado_audio_pendiente:
            raise serializers.ValidationError({"error": "Falta configurar el Estado Audio 'PENDIENTE' en la BD."})
        validated_data['id_estado_audios'] = estado_audio_pendiente

        # Lógica de audio: Nace en False siempre
        validated_data['audio_subido'] = False
        validated_data['fecha_subida_audios'] = None

        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user

        # 1. AUDITORÍA BASE
        validated_data['usuario_modificacion'] = user

        # Variables clave
        nueva_fecha_visita = validated_data.get('fecha_visita_programada')
        nuevo_sub_estado = validated_data.get('id_sub_estado_sot')
        nuevo_estado_sot = validated_data.get('id_estado_sot')
        nuevo_estado_audio = validated_data.get('id_estado_audios')
        nuevo_comentario = validated_data.get('comentario_gestion')

        fecha_visita_antigua = instance.fecha_visita_programada

        with transaction.atomic():

            # ==========================================
            # VALIDACIÓN DE REGLA DE NEGOCIO: COMENTARIO
            # ==========================================
            # Si intentan guardar un comentario, verificamos que el estado sea RECHAZADO
            if nuevo_comentario:
                estado_evaluar = nuevo_estado_sot if nuevo_estado_sot else instance.id_estado_sot
                if estado_evaluar.codigo != 'RECHAZADO':
                    raise serializers.ValidationError({
                        "comentario_gestion": "Solo se puede agregar un comentario de gestión si el estado es RECHAZADO."
                    })

            # ==========================================
            # 2. TRIGGER DE AUDIOS (Revisión de Backoffice)
            # ==========================================
            if nuevo_estado_audio and nuevo_estado_audio != instance.id_estado_audios:
                validated_data['usuario_revision_audios'] = user
                validated_data['fecha_revision_audios'] = timezone.now()

            # ==========================================
            # 3. TRIGGER DE ESTADOS FINALES (SOT)
            # ==========================================
            if nuevo_estado_sot and nuevo_estado_sot != instance.id_estado_sot:
                # Si pasa a RECHAZADO y no hay fecha manual, la ponemos
                if nuevo_estado_sot.codigo == 'RECHAZADO' and not validated_data.get('fecha_rechazo'):
                    validated_data['fecha_rechazo'] = timezone.now()

                # Si pasa a FINAL (ATENDIDO) y no es rechazado, ponemos fecha instalacion
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
            if nueva_fecha_visita and nueva_fecha_visita != fecha_visita_antigua:
                if nuevo_sub_estado and nuevo_sub_estado.requiere_nueva_fecha:
                    HistorialAgendaSOT.objects.create(
                        id_venta=instance,
                        fecha_anterior=fecha_visita_antigua,
                        fecha_nueva=nueva_fecha_visita,
                        id_sub_estado_motivo=nuevo_sub_estado,
                        usuario_responsable=user
                    )

        return instance