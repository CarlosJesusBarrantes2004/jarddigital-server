from rest_framework import serializers
from django.utils import timezone
from django.db.models import Q
from .models import EstadoSOT, SubEstadoSOT, EstadoAudio, Producto, GrabadorAudio, Venta, AudioVenta
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
            'nombre_campana',
            'tipo_solucion',
            'nombre_paquete',
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


class AudioVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioVenta
        fields = ['id', 'nombre_etiqueta', 'url_audio', 'conforme', 'motivo', 'corregido']
        extra_kwargs = {
            'id': {'read_only': False, 'required': False}, # Clave para el PATCH futuro
            'conforme': {'required': False, 'allow_null': True},
            'motivo': {'required': False, 'allow_null': True},
            'corregido': {'read_only': True}
        }


class VentaSerializer(serializers.ModelSerializer):
    # Campos visuales de solo lectura
    nombre_asesor = serializers.CharField(source='id_asesor.nombre_completo', read_only=True)

    # Campos del producto separados
    producto_campana = serializers.CharField(source='id_producto.nombre_campana', read_only=True)
    producto_solucion = serializers.CharField(source='id_producto.tipo_solucion', read_only=True)
    producto_paquete = serializers.CharField(source='id_producto.nombre_paquete', read_only=True)

    nombre_estado = serializers.CharField(source='id_estado_sot.nombre', read_only=True)
    codigo_estado = serializers.CharField(source="id_estado_sot.codigo", read_only=True)
    nombre_supervisor = serializers.CharField(source='id_supervisor_vigente.id_supervisor.nombre_completo',
                                              read_only=True)
    codigo_tipo_documento = serializers.CharField(source="id_tipo_documento.codigo", read_only=True)

    # 1. Creamos un campo dinámico para el nombre final del Grabador
    grabador_real = serializers.SerializerMethodField(read_only=True)

    # 1. Declaramos los nuevos campos calculados
    codigo_sec_origen = serializers.SerializerMethodField(read_only=True)
    codigo_sot_origen = serializers.SerializerMethodField(read_only=True)

    # ---> ¡NUEVO CAMPO ANIDADO! <---
    # El nombre de la variable "audios" DEBE coincidir con el related_name="audios" de tu models.py
    audios = AudioVentaSerializer(many=True, required=False)

    class Meta:
        model = Venta
        fields = '__all__'

        read_only_fields = [
            'id_asesor', 'id_origen_venta', 'id_supervisor_vigente',
            'usuario_creacion', 'fecha_creacion', 'usuario_modificacion', 'fecha_modificacion',
            'tipo_venta'
        ]

        extra_kwargs = {
            'id_estado_sot': {'required': False, 'allow_null': True},
            'id_estado_audios': {'required': False},

            # Obligatorios para Asesor
            'cliente_email': {'required': True, 'allow_null': False},
            "cliente_genero": {"required": True, "allow_null": False},
            'coordenadas_gps': {'required': True, 'allow_null': False},
            'score_crediticio': {'required': True, 'allow_null': False},
            'fecha_venta': {'required': False, 'allow_null': True},
            "permitir_reingreso": {"required": False},
            'id_grabador_audios': {'required': True, 'allow_null': False},

            # 2. Permitimos que el frontend envíe el ID de la venta origen
            "venta_origen": {"required": False, "allow_null": True},
        }

    # Lógica para decidir qué nombre de Grabador enviar
    def get_grabador_real(self, obj):
        # Verificamos que la venta tenga un grabador asignado
        if obj.id_grabador_audios:
            # Si es el ID 1 (OTROS) y tiene un nombre externo guardado
            if obj.id_grabador_audios.id == 1 and obj.nombre_grabador_externo:
                return f"{obj.nombre_grabador_externo} (Externo)"

            # Si es cualquier otro grabador normal, devolvemos su nombre oficial
            return obj.id_grabador_audios.nombre_completo

        return None

    # 3. Métodos para obtener los datos de la venta origen
    def get_codigo_sec_origen(self, obj):
        if obj.venta_origen_id:
            return obj.venta_origen.codigo_sec
        return None

    def get_codigo_sot_origen(self, obj):
        if obj.venta_origen_id:
            return obj.venta_origen.codigo_sot
        return None

    def validate(self, data):
        # Extraemos el usuario al inicio para usarlo en cualquier validación (Creación o Edición)
        request = self.context.get('request')
        user = request.user if request else None
        es_asesor = (user and hasattr(user, 'id_rol') and user.id_rol and user.id_rol.codigo.upper() == 'ASESOR')

        # =======================================================
        # CANDADO ANTI-TRAMPAS PARA REINGRESOS
        # =======================================================
        # Si un asesor intenta enviarnos este campo (sea creando o editando), lo borramos silenciosamente.
        if es_asesor and 'permitir_reingreso' in data:
            data.pop('permitir_reingreso')

        # =======================================================
        # 0. CANDADOS DE SEGURIDAD Y PERMISOS (ASESOR)
        # =======================================================
        if self.instance:  # Solo aplica si es EDICIÓN (PATCH/PUT)
            if es_asesor:
                estado_actual = self.instance.id_estado_sot.codigo.upper() if self.instance.id_estado_sot else ""

                # ¡LA CORRECCIÓN MÁESTRA!
                # Le preguntamos a la base de datos si esta venta ya tiene archivos de audio adjuntos.
                ya_tiene_audios = self.instance.audios.exists()

                # --- REGLA 1: PUERTA ABIERTA (Solo si tiene 0 audios en nuestra BD) ---
                if estado_actual == 'EJECUCION' and not ya_tiene_audios:
                    campos_enviados = set(data.keys())
                    # Solo le dejamos tocar la llave 'audios'
                    campos_prohibidos = [campo for campo in campos_enviados if campo != 'audios']

                    if campos_prohibidos:
                        raise serializers.ValidationError({
                            "bloqueo_parcial": f"Aún te falta subir los audios, pero NO puedes editar otros datos de la venta. Campos prohibidos detectados: {', '.join(campos_prohibidos)}"
                        })

                # --- REGLA 2: PUERTA CERRADA (La Papa Caliente estricta) ---
                # Si ya subió los audios y NO tiene el permiso explícito del backoffice, se bloquea todo.
                elif not getattr(self.instance, 'solicitud_correccion', False):
                    raise serializers.ValidationError({
                        "bloqueo_total": "Los audios ya fueron subidos a nuestro sistema. Espera a que el Backoffice los revise y te solicite una corrección para poder editar."
                    })

        # =======================================================
        # C. VALIDACIÓN DE VENTA ORIGEN (Regla de pertenencia)
        # =======================================================
        # Extraemos la venta origen si es que la enviaron en el JSON
        venta_origen = data.get('venta_origen')

        # Si enviaron una venta origen y quien está guardando es un ASESOR...
        if venta_origen and es_asesor:
            # Comparamos el ID del asesor de la venta antigua con el usuario actual
            if venta_origen.id_asesor != user:
                raise serializers.ValidationError({
                    "venta_origen": "Acceso denegado: Solo puedes vincular una venta origen que haya sido gestionada por ti."
                })

        # =======================================================
        # D. VALIDACIÓN DE COINCIDENCIA DE MODALIDAD (Sede vs Supervisor)
        # =======================================================
        # Extraemos los datos del JSON entrante o de la base de datos si es una edición parcial (PATCH)
        origen_venta = data.get('id_origen_venta', getattr(self.instance, 'id_origen_venta', None))
        asignacion_supervisor = data.get('id_supervisor_vigente',
                                            getattr(self.instance, 'id_supervisor_vigente', None))

        if origen_venta and asignacion_supervisor:
            # Obtenemos la sede/modalidad a la que está realmente asignado el supervisor
            # (Ajusta 'id_modalidad_sede' si tu modelo de asignación lo llama de otra forma)
            sede_del_supervisor = asignacion_supervisor.id_modalidad_sede

            # Si la sede de la venta no es la misma que la sede del supervisor, bloqueamos
            if origen_venta != sede_del_supervisor:
                raise serializers.ValidationError({
                    "id_supervisor_vigente": "Error de seguridad: El supervisor seleccionado pertenece a una modalidad/sede distinta a la de esta venta."
                })

        # =======================================================
        # E. VALIDACIÓN DE GRABADOR "OTROS" (ID 1)
        # =======================================================
        grabador = data.get('id_grabador_audios', getattr(self.instance, 'id_grabador_audios', None))
        nombre_externo = data.get('nombre_grabador_externo',
                                    getattr(self.instance, 'nombre_grabador_externo', None))

        if grabador:
            # Si el ID del grabador es 1 (OTROS)
            if grabador.id == 1:
                # Exigimos que el nombre externo venga lleno y no sean puros espacios
                if not nombre_externo or str(nombre_externo).strip() == "":
                    raise serializers.ValidationError({
                        "nombre_grabador_externo": "Al seleccionar 'OTROS' como grabador, es obligatorio especificar el nombre de la persona."
                    })
            else:
                # Si es un grabador normal de la empresa, limpiamos el campo externo por seguridad
                if not self.instance or 'nombre_grabador_externo' in data:
                    data['nombre_grabador_externo'] = None

        # =======================================================
        # 1. VALIDACIÓN DE DOCUMENTOS Y REPRESENTANTE LEGAL
        # =======================================================
        tipo_doc = data.get('id_tipo_documento', getattr(self.instance, 'id_tipo_documento', None))

        if tipo_doc:
            codigo_doc = tipo_doc.codigo.upper()
            es_ruc = (codigo_doc == "RUC")
            es_dni = (codigo_doc == "DNI")

            # A. VALIDACIÓN DE REPRESENTANTE LEGAL (Solo RUC)
            rep_dni = data.get('representante_legal_dni', getattr(self.instance, 'representante_legal_dni', None))
            rep_nombre = data.get('representante_legal_nombre',
                                  getattr(self.instance, 'representante_legal_nombre', None))

            if es_ruc:
                errores = {}
                if not rep_dni:
                    errores['representante_legal_dni'] = "El DNI del representante es obligatorio cuando es RUC."
                if not rep_nombre:
                    errores['representante_legal_nombre'] = "El nombre del representante es obligatorio cuando es RUC."

                if errores:
                    raise serializers.ValidationError(errores)
            else:
                if not self.instance or 'representante_legal_dni' in data:
                    data['representante_legal_dni'] = None
                if not self.instance or 'representante_legal_nombre' in data:
                    data['representante_legal_nombre'] = None

            # =======================================================
            # REGLA 3: AUDIOS "TODO O NADA" (Aplica en Creación y Edición)
            # =======================================================
            audios_data = data.get('audios')

            if audios_data is not None:
                cantidad_audios = len(audios_data)

                # Averiguamos si la venta ya tenía audios de antes
                ya_tiene_audios = self.instance.audios.exists() if self.instance else False

                # SOLO exigimos los 12 o 14 si es la primera vez que sube audios
                if not ya_tiene_audios and cantidad_audios > 0:
                    if es_dni and cantidad_audios != 12:
                        raise serializers.ValidationError({
                            "audios": f"Para la primera subida, debes enviar TODOS los audios obligatorios (12 para DNI). Has intentado subir {cantidad_audios}."
                        })
                    elif es_ruc and cantidad_audios != 14:
                        raise serializers.ValidationError({
                            "audios": f"Para la primera subida, debes enviar TODOS los audios obligatorios (14 para RUC). Has intentado subir {cantidad_audios}."
                        })
        return data


    def create(self, validated_data):
        # 1. INTERCEPTAMOS LA LISTA DE AUDIOS ANTES DE CREAR LA VENTA
        audios_data = validated_data.pop('audios', [])

        # -------------------------------------------------------
        # CÁLCULO AUTOMÁTICO DE TIPO DE VENTA (MASIVO vs CORP)
        # -------------------------------------------------------
        tipo_doc = validated_data.get('id_tipo_documento')
        if tipo_doc:
            if tipo_doc.codigo.upper() == 'RUC':
                validated_data['tipo_venta'] = 'CORPORATIVO'
            else:
                # Asumimos que DNI, CE, Pasaporte, etc. son MASIVO
                validated_data['tipo_venta'] = 'MASIVO'

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
            'audio_subido', 'fecha_venta'
        ]
        for campo in campos_backoffice:
            validated_data.pop(campo, None)

        validated_data['id_estado_sot'] = None
        estado_audio_pendiente = EstadoAudio.objects.filter(codigo='PENDIENTE').first()
        validated_data['id_estado_audios'] = estado_audio_pendiente
        validated_data['audio_subido'] = False
        validated_data['fecha_subida_audios'] = None
        validated_data['fecha_venta'] = None

        # 2. CREAMOS LA VENTA PRINCIPAL (El super() ahora no fallará porque ya le quitamos 'audios')
        venta_creada = super().create(validated_data)

        # 3. GUARDAMOS LOS AUDIOS AMARRADOS A LA VENTA
        for audio_item in audios_data:
            # Los audios nacen con conforme=None y motivo=None por defecto
            AudioVenta.objects.create(id_venta=venta_creada, **audio_item)

        return venta_creada

    def update(self, instance, validated_data):
        # Extraemos el usuario y su rol primero (Lo necesitamos para el candado)
        request = self.context.get('request')
        user = request.user
        es_backoffice = (user.id_rol and user.id_rol.codigo.upper() == 'BACKOFFICE')

        # =======================================================
        # 0. CANDADO DE INMUTABILIDAD (REGLA DEL PRODUCT OWNER)
        # =======================================================
        if instance.id_estado_sot and instance.id_estado_sot.codigo.upper() == 'RECHAZADO':
            # Y el que intenta editarla NO es el Backoffice...
            if not es_backoffice:
                raise serializers.ValidationError({
                    "error_critico": "Esta venta ha sido RECHAZADA y está cerrada permanentemente. Para corregirla, debes generar una nueva venta."
                })

        # ---> ¡NUEVO: INTERCEPTAR AUDIOS! <---
        # Usamos None por defecto para saber si enviaron o no la llave "audios" en el PATCH
        audios_data = validated_data.pop('audios', None)

        # -------------------------------------------------------
        # RE-CÁLCULO AUTOMÁTICO SI CAMBIA EL DOCUMENTO
        # -------------------------------------------------------
        nuevo_tipo_doc = validated_data.get('id_tipo_documento')

        # Solo recalculamos si están enviando un documento nuevo
        if nuevo_tipo_doc:
            if nuevo_tipo_doc.codigo.upper() == 'RUC':
                validated_data['tipo_venta'] = 'CORPORATIVO'
            else:
                validated_data['tipo_venta'] = 'MASIVO'

        # Asignamos el usuario que modifica (Ya lo extrajimos arriba)
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
            # 1. GATILLOS DE AUDIO Y FECHAS (PRIORIDAD ABSOLUTA)
            # =======================================================
            if audio_subido_flag is True and not instance.audio_subido:
                validated_data['fecha_subida_audios'] = timezone.now()

            nuevo_estado_audio = validated_data.get('id_estado_audios')
            if nuevo_estado_audio and nuevo_estado_audio != instance.id_estado_audios:
                validated_data['usuario_revision_audios'] = user
                validated_data['fecha_revision_audios'] = timezone.now()

                # Usamos .upper() para evitar problemas de mayúsculas/minúsculas en BD
                if nuevo_estado_audio.codigo.upper() == 'RECHAZADO':

                    # FORZAMOS EL ESTADO SOT A RECHAZADO (OVERRIDE)
                    estado_rechazado = EstadoSOT.objects.filter(codigo__iexact='RECHAZADO').first()
                    if estado_rechazado:
                        validated_data['id_estado_sot'] = estado_rechazado

                    # Validaciones obligatorias de rechazo
                    if not validated_data.get('fecha_rechazo') and not instance.fecha_rechazo:
                        raise serializers.ValidationError({
                            "fecha_rechazo": "Al rechazar por audio, también debe indicar la fecha de rechazo de la venta."
                        })

                    observacion = validated_data.get('observacion_audios')
                    if not observacion and not instance.observacion_audios:
                        raise serializers.ValidationError(
                            {"observacion_audios": "Observación obligatoria al rechazar el audio."}
                        )

            # =======================================================
            # 2. ESTAMPADO DE FECHA DE VENTA (INDEPENDIENTE)
            # =======================================================
            # Si entran códigos SOT/SEC por primera vez, sellamos la fecha
            if (nuevo_codigo_sot and not instance.codigo_sot) or (nuevo_codigo_sec and not instance.codigo_sec):
                if not instance.fecha_venta:
                    validated_data['fecha_venta'] = timezone.now()

            # =======================================================
            # 3. AUTOMATIZACIONES DE ESTADO SOT
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
            # 4. DEFINIR ESTADO DESTINO FINAL PARA VALIDACIONES
            # =======================================================
            estado_destino = validated_data['id_estado_sot'] if 'id_estado_sot' in validated_data else instance.id_estado_sot
            estado_audio_destino = validated_data['id_estado_audios'] if 'id_estado_audios' in validated_data else instance.id_estado_audios

            # =======================================================
            # 4.5 REGLA: EJECUCIÓN EXIGE CÓDIGOS SOT/SEC
            # =======================================================
            if estado_destino and estado_destino.codigo.upper() == 'EJECUCION':
                # Verificamos si ya los tiene (instance) o si los están mandando ahora (validated_data)
                tiene_sot = instance.codigo_sot or validated_data.get('codigo_sot')
                tiene_sec = instance.codigo_sec or validated_data.get('codigo_sec')

                if not tiene_sot or not tiene_sec:
                    raise serializers.ValidationError({
                        "codigo_sot": "Para pasar la venta a EJECUCIÓN, es obligatorio registrar el código SOT y el código SEC."
                    })

            # =======================================================
            # 5. REGLA: ATENDIDO vs AUDIOS
            # =======================================================
            if estado_destino and estado_destino.codigo.upper() == 'ATENDIDO':
                if not estado_audio_destino or estado_audio_destino.codigo.upper() != 'CONFORME':
                    raise serializers.ValidationError({
                        "id_estado_sot": "Bloqueado: No se puede pasar a ATENDIDO si los audios no están en CONFORME."
                    })

            # =======================================================
            # 6. VALIDACIÓN DE FECHAS MANUALES SEGÚN DESTINO
            # =======================================================
            if estado_destino:
                if estado_destino.codigo.upper() == 'RECHAZADO':
                    fecha_rechazo_input = validated_data.get('fecha_rechazo')
                    if not fecha_rechazo_input and not instance.fecha_rechazo:
                        raise serializers.ValidationError(
                            {"fecha_rechazo": "Debe ingresar la fecha de rechazo manualmente."}
                        )

                elif estado_destino.codigo.upper() == 'ATENDIDO':
                    fecha_inst_input = validated_data.get('fecha_real_inst')
                    if not fecha_inst_input and not instance.fecha_real_inst:
                        raise serializers.ValidationError(
                            {"fecha_real_inst": "Debe ingresar la fecha real de instalación."}
                        )

            # =======================================================
            # 7. VALIDACIÓN SUB-ESTADO
            # =======================================================
            if nuevo_sub_estado:
                if not estado_destino or estado_destino.codigo.upper() != 'EJECUCION':
                    raise serializers.ValidationError({
                        "id_sub_estado_sot": "El sub-estado solo se puede asignar si el Estado SOT es 'EJECUCIÓN'."
                    })

            # =======================================================
            # 8. GUARDADO FINAL
            # =======================================================
            # Detectamos quién está guardando
            es_asesor = (user.id_rol and user.id_rol.codigo == 'ASESOR')

            # Si el ASESOR está guardando cambios...
            if es_asesor:
                # 1. Apagamos la solicitud de corrección (La papa vuelve al Backoffice)
                validated_data['solicitud_correccion'] = False
                # 2. (Opcional) Limpiamos el comentario del Backoffice para que no confunda
                validated_data['comentario_gestion'] = None

            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # =======================================================
            # 8.5 EL MONSTRUO: ACTUALIZACIÓN ANIDADA DE AUDIOS
            # =======================================================
            if audios_data is not None:
                # 1. Creamos un diccionario mágico { ID_Audio: Objeto_Audio }
                # Esto evita hacer 14 consultas a la BD. Hacemos 1 sola y mapeamos.
                audios_existentes = {audio.id: audio for audio in instance.audios.all()}

                for audio_item in audios_data:
                    audio_id = audio_item.get('id')

                    if audio_id and audio_id in audios_existentes:
                        # ---> ESCENARIO A: ACTUALIZAR AUDIO EXISTENTE <---
                        audio_instance = audios_existentes[audio_id]

                        # -----------------------------------------------------------
                        # A1. DETECCIÓN DE NUEVA VERSIÓN (ASESOR CORRIGE EL AUDIO)
                        # -----------------------------------------------------------
                        nueva_url = audio_item.get('url_audio')
                        url_anterior = audio_instance.url_audio

                        # Si viene una URL nueva y es distinta a la anterior...
                        if nueva_url and nueva_url != url_anterior:
                            audio_instance.url_audio = nueva_url
                            audio_instance.conforme = None  # Reiniciamos a "Pendiente"
                            audio_instance.motivo = None  # Limpiamos la queja anterior
                            audio_instance.corregido = True  # ¡BANDERA ARRIBA! Avisamos a Jadira

                        # -----------------------------------------------------------
                        # A2. ACTUALIZACIÓN DE ETIQUETA (SI CAMBIÓ)
                        # -----------------------------------------------------------
                        audio_instance.nombre_etiqueta = audio_item.get('nombre_etiqueta',
                                                                        audio_instance.nombre_etiqueta)

                        # -----------------------------------------------------------
                        # A3. DETECCIÓN DE REVISIÓN (BACKOFFICE RESPONDE)
                        # -----------------------------------------------------------
                        # Si viene 'conforme' (True o False), significa que Jadira lo revisó.
                        if 'conforme' in audio_item:
                            audio_instance.conforme = audio_item['conforme']
                            # Al emitir veredicto, la bandera de "aviso" se apaga.
                            audio_instance.corregido = False

                        if 'motivo' in audio_item:
                            audio_instance.motivo = audio_item['motivo']

                        audio_instance.save()

                    else:
                        # ---> ESCENARIO B: CREAR NUEVO AUDIO <---
                        # Por si el Asesor olvidó un audio en el POST original y lo manda ahora
                        # (Nota: Nacen con corregido=False por defecto en el modelo)
                        AudioVenta.objects.create(id_venta=instance, **audio_item)


            # =======================================================
            # 9. HISTORIAL DE AGENDA
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