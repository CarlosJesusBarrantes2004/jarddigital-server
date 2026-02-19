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
    # Campos visuales de solo lectura
    nombre_asesor = serializers.CharField(source='id_asesor.nombre_completo', read_only=True)
    nombre_producto = serializers.CharField(source='id_producto.nombre_plan', read_only=True)
    nombre_estado = serializers.CharField(source='id_estado_sot.nombre', read_only=True)
    nombre_supervisor = serializers.CharField(source='id_supervisor_vigente.id_supervisor.nombre_completo',
                                              read_only=True)

    class Meta:
        model = Venta
        fields = '__all__'

        read_only_fields = [
            'id_asesor', 'id_origen_venta', 'id_supervisor_vigente',
            'usuario_creacion', 'fecha_creacion', 'usuario_modificacion', 'fecha_modificacion'
        ]

        extra_kwargs = {
            'id_estado_sot': {'required': False, 'allow_null': True},
            'id_estado_audios': {'required': False},

            # Obligatorios para Asesor
            'cliente_email': {'required': True, 'allow_null': False},
            'coordenadas_gps': {'required': True, 'allow_null': False},
            'score_crediticio': {'required': True, 'allow_null': False},
            'id_grabador_audios': {'required': True, 'allow_null': False}
        }

    def create(self, validated_data):
        # ... (El método create se mantiene IGUAL que la versión anterior) ...
        request = self.context.get('request')
        user = request.user

        validated_data['id_asesor'] = user
        validated_data['usuario_creacion'] = user

        permiso_sede = PermisoAcceso.objects.filter(
            id_usuario=user, id_modalidad_sede__activo=True
        ).select_related('id_modalidad_sede').first()

        if not permiso_sede:
            raise serializers.ValidationError({"error": "No tienes Sede asignada."})
        validated_data['id_origen_venta'] = permiso_sede.id_modalidad_sede

        hoy = timezone.now().date()
        supervisor_activo = SupervisorAsignacion.objects.filter(
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy),
            id_modalidad_sede=permiso_sede.id_modalidad_sede,
            activo=True
        ).first()

        if not supervisor_activo:
            raise serializers.ValidationError({"error": "La sede no tiene supervisor activo hoy."})
        validated_data['id_supervisor_vigente'] = supervisor_activo

        campos_backoffice = [
            'codigo_sec', 'codigo_sot', 'fecha_visita_programada', 'bloque_horario', 'id_sub_estado_sot',
            'fecha_real_inst', 'fecha_rechazo', 'comentario_gestion',
            'fecha_revision_audios', 'usuario_revision_audios', 'observacion_audios',
            'audio_subido'
        ]
        for campo in campos_backoffice:
            validated_data.pop(campo, None)

        validated_data['id_estado_sot'] = None
        estado_audio_pendiente = EstadoAudio.objects.filter(codigo='PENDIENTE').first()
        validated_data['id_estado_audios'] = estado_audio_pendiente
        validated_data['audio_subido'] = False
        validated_data['fecha_subida_audios'] = None

        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user
        validated_data['usuario_modificacion'] = user

        # Extraemos variables de entrada
        nuevo_codigo_sot = validated_data.get('codigo_sot')
        nuevo_codigo_sec = validated_data.get('codigo_sec')
        nuevo_sub_estado = validated_data.get('id_sub_estado_sot')
        audio_subido_flag = validated_data.get('audio_subido')
        nueva_fecha_inst = validated_data.get('fecha_real_inst')

        fecha_visita_antigua = instance.fecha_visita_programada
        estado_sot_antiguo = instance.id_estado_sot

        with transaction.atomic():

            # =======================================================
            # 0. GATILLOS DE AUDIO Y FECHAS (PRIORIDAD ABSOLUTA)
            # =======================================================
            if audio_subido_flag is True and not instance.audio_subido:
                validated_data['fecha_subida_audios'] = timezone.now()

            nuevo_estado_audio = validated_data.get('id_estado_audios')
            if nuevo_estado_audio and nuevo_estado_audio != instance.id_estado_audios:
                validated_data['usuario_revision_audios'] = user
                validated_data['fecha_revision_audios'] = timezone.now()

                # Usamos .upper() para evitar problemas de mayúsculas/minúsculas en BD
                if nuevo_estado_audio.codigo.upper() == 'RECHAZADO':

                    # 1. FORZAMOS EL ESTADO SOT A RECHAZADO (OVERRIDE)
                    estado_rechazado = EstadoSOT.objects.filter(codigo__iexact='RECHAZADO').first()
                    if estado_rechazado:
                        validated_data['id_estado_sot'] = estado_rechazado

                    # 2. Validaciones obligatorias de rechazo
                    if not validated_data.get('fecha_rechazo') and not instance.fecha_rechazo:
                        raise serializers.ValidationError({
                                                              "fecha_rechazo": "Al rechazar por audio, también debe indicar la fecha de rechazo de la venta."})

                    observacion = validated_data.get('observacion_audios')
                    if not observacion and not instance.observacion_audios:
                        raise serializers.ValidationError(
                            {"observacion_audios": "Observación obligatoria al rechazar el audio."})

            # =======================================================
            # 1. AUTOMATIZACIONES DE ESTADO SOT
            # =======================================================
            # Verificamos si la validación anterior de audio modificó el estado
            if 'id_estado_sot' not in validated_data:

                # A. Si mandan fecha de instalación -> Sugerir ATENDIDO
                if nueva_fecha_inst:
                    estado_atendido = EstadoSOT.objects.filter(codigo__iexact='ATENDIDO').first()
                    if estado_atendido:
                        validated_data['id_estado_sot'] = estado_atendido

                # B. Si ingresan códigos SEC/SOT -> Sugerir EJECUCION
                elif (nuevo_codigo_sot and not instance.codigo_sot) or (nuevo_codigo_sec and not instance.codigo_sec):
                    estado_ejecucion = EstadoSOT.objects.filter(codigo__iexact='EJECUCION').first()
                    if estado_ejecucion:
                        validated_data['id_estado_sot'] = estado_ejecucion

            # =======================================================
            # 2. DEFINIR ESTADO DESTINO FINAL PARA VALIDACIONES
            # =======================================================
            estado_destino = validated_data[
                'id_estado_sot'] if 'id_estado_sot' in validated_data else instance.id_estado_sot
            estado_audio_destino = validated_data[
                'id_estado_audios'] if 'id_estado_audios' in validated_data else instance.id_estado_audios

            # =======================================================
            # 3. REGLA: REVIVIR VENTA (RECHAZADO -> EJECUCION)
            # =======================================================
            if estado_sot_antiguo and estado_sot_antiguo.codigo.upper() == 'RECHAZADO':
                if estado_destino and estado_destino.codigo.upper() == 'EJECUCION':
                    # ¡NUEVO CANDADO!: Si reviven la venta, exijimos códigos nuevos
                    if not nuevo_codigo_sec or not nuevo_codigo_sot:
                        raise serializers.ValidationError({
                            "codigo_sot": "Para revivir una venta a EJECUCIÓN, es obligatorio enviar el nuevo codigo_sec y codigo_sot."
                        })

                    # Limpiamos el historial de rechazo
                    validated_data['fecha_rechazo'] = None

            # =======================================================
            # 4. REGLA: ATENDIDO vs AUDIOS
            # =======================================================
            if estado_destino and estado_destino.codigo.upper() == 'ATENDIDO':
                if not estado_audio_destino or estado_audio_destino.codigo.upper() != 'CONFORME':
                    raise serializers.ValidationError({
                        "id_estado_sot": "Bloqueado: No se puede pasar a ATENDIDO si los audios no están en CONFORME."
                    })

            # =======================================================
            # 5. VALIDACIÓN DE FECHAS MANUALES SEGÚN DESTINO
            # =======================================================
            if estado_destino:
                if estado_destino.codigo.upper() == 'RECHAZADO':
                    fecha_rechazo_input = validated_data.get('fecha_rechazo')
                    if not fecha_rechazo_input and not instance.fecha_rechazo:
                        raise serializers.ValidationError(
                            {"fecha_rechazo": "Debe ingresar la fecha de rechazo manualmente."})

                elif estado_destino.codigo.upper() == 'ATENDIDO':
                    fecha_inst_input = validated_data.get('fecha_real_inst')
                    if not fecha_inst_input and not instance.fecha_real_inst:
                        raise serializers.ValidationError(
                            {"fecha_real_inst": "Debe ingresar la fecha real de instalación."})

            # =======================================================
            # 6. VALIDACIÓN SUB-ESTADO
            # =======================================================
            if nuevo_sub_estado:
                if not estado_destino or estado_destino.codigo.upper() != 'EJECUCION':
                    raise serializers.ValidationError({
                        "id_sub_estado_sot": "El sub-estado solo se puede asignar si el Estado SOT es 'EJECUCIÓN'."
                    })

            # =======================================================
            # 7. GUARDADO FINAL
            # =======================================================
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # =======================================================
            # 8. HISTORIAL DE AGENDA
            # =======================================================
            nueva_fecha_visita = validated_data.get('fecha_visita_programada')
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