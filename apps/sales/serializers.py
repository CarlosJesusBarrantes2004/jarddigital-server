from rest_framework import serializers
from .models import EstadoSOT, SubEstadoSOT, EstadoAudio, Producto, GrabadorAudio, Venta, AudioVenta
from apps.users.models import SupervisorAsignacion, PermisoAcceso
from apps.sales.models import HistorialAgendaSOT
from apps.sales.services import crear_venta, actualizar_venta

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
    celular_asesor = serializers.CharField(
        source="id_asesor.celular", allow_null=True, read_only=True
    )

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

    # Campos de ubigeo de instalación (solo lectura)
    distrito_instalacion_nombre = serializers.CharField(source='id_distrito_instalacion.nombre', read_only=True)
    provincia_instalacion_nombre = serializers.CharField(source='id_distrito_instalacion.id_provincia.nombre', read_only=True)
    departamento_instalacion_nombre = serializers.CharField(source='id_distrito_instalacion.id_provincia.id_departamento.nombre', read_only=True)

    # Campos de UBIGEO de Cliente
    distrito_nacimiento_nombre = serializers.CharField(source="id_distrito_nacimiento.nombre", read_only=True, default=None)
    provincia_nacimiento_nombre = serializers.CharField(source="id_distrito_nacimiento.id_provincia.nombre", read_only=True, default=None)
    departamento_nacimiento_nombre = serializers.CharField(source="id_distrito_nacimiento.id_provincia.id_departamento.nombre", read_only=True, default=None)

    # ---> NUEVO CAMPO <---
    ya_reingresada = serializers.SerializerMethodField(read_only=True)

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
            'id_grabador_audios': {'required': False, 'allow_null': True},

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

    # ---> FIX #8: NUEVO MÉTODO DE CLAUDE <---
    def get_ya_reingresada(self, obj):
        """
        Lee el atributo virtual inyectado por el Selector para evitar consultas extra.
        """
        # 1. Si la venta viene del listado (Selector), ya trae el cálculo hecho en SQL
        if hasattr(obj, '_ya_reingresada'):
            return obj._ya_reingresada

        # 2. Fallback de seguridad: Por si alguien consulta una sola venta
        # sin pasar por el selector (ej. justo después de crearla)
        return obj.ventas_derivadas.filter(activo=True).exists()


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

                # Extraemos el código del estado (si no tiene, será un string vacío "")
                estado_actual = self.instance.id_estado_sot.codigo.upper() if self.instance.id_estado_sot else ""

                ya_tiene_audios = bool(self.instance.audios.all())
                tiene_permiso_backoffice = getattr(self.instance, 'solicitud_correccion', False)

                # --- REGLA 0: EL CANDADO DE LA MUERTE (Venta Rechazada) ---
                if estado_actual in ['RECHAZADO', 'RECHAZADA']:
                    raise serializers.ValidationError({
                        "error_critico": "Esta venta ha sido RECHAZADA permanentemente. No puedes subir audios ni editarla. Debes generar una nueva venta."
                    })

                # --- REGLA 1: PUERTA ABIERTA ---
                if not ya_tiene_audios and estado_actual in ['EJECUCION', '']:
                    if not tiene_permiso_backoffice:
                        campos_enviados = set(data.keys())
                        campos_permitidos_sin_backoffice = {
                            "audios",
                            "id_grabador_audios",
                            "nombre_grabador_externo",
                        }
                        campos_prohibidos = [
                            campo for campo in campos_enviados
                            if campo not in campos_permitidos_sin_backoffice
                        ]
                        if campos_prohibidos:
                            raise serializers.ValidationError({
                                "bloqueo_parcial": f"Aún te falta subir los audios iniciales, pero NO tienes permiso para editar otros datos de la venta. Campos prohibidos detectados: {', '.join(campos_prohibidos)}"
                            })

                # --- REGLA 2: PUERTA CERRADA (Cualquier otro escenario) ---
                else:
                    # Cayó aquí porque: o ya subió sus audios, o la venta está en un estado avanzado (ej. ATENDIDO).
                    # Exigimos SÍ O SÍ la llave del Backoffice para dejarlo pasar.
                    if not tiene_permiso_backoffice:
                        motivo = "Los audios ya fueron subidos a nuestro sistema." if ya_tiene_audios else f"La venta se encuentra en estado {estado_actual}."
                        raise serializers.ValidationError({
                            "bloqueo_total": f"{motivo} Espera a que el Backoffice revise y te habilite una solicitud de corrección para poder editar."
                        })

        # =======================================================
        # C. VALIDACIÓN DE VENTA ORIGEN (Regla de pertenencia)
        # =======================================================
        # Extraemos la venta origen si es que la enviaron en el JSON
        venta_origen = data.get('venta_origen')

        if venta_origen:
            # --- 1. REGLA DE PERTENENCIA ---
            # Si quien está guardando es un ASESOR...
            if es_asesor:
                if venta_origen.id_asesor != user:
                    raise serializers.ValidationError({
                        "venta_origen": "Acceso denegado: Solo puedes vincular una venta origen que haya sido gestionada por ti."
                    })

            # --- 2. REGLA ANTI-FRAUDE DE GRABADOR (Reingresos) ---
            # Extraemos el DNI y Grabador entrantes (o los actuales si es un PATCH)
            nuevo_doc = data.get('cliente_numero_doc', getattr(self.instance, 'cliente_numero_doc', None))
            nuevo_grabador = data.get('id_grabador_audios', getattr(self.instance, 'id_grabador_audios', None))

            viejo_doc = venta_origen.cliente_numero_doc
            viejo_grabador = venta_origen.id_grabador_audios

            # Validamos los escenarios de reingreso (solo si enviaron un DNI para evaluar)
            if nuevo_doc and viejo_doc:

                # Escenario A: El cliente es el mismo
                if nuevo_doc == viejo_doc:
                    if viejo_grabador and nuevo_grabador != viejo_grabador:
                        raise serializers.ValidationError({
                            "id_grabador_audios": "Regla de Reingreso: Como el Documento es idéntico a la venta original, debes mantener el mismo Grabador de Audio."
                        })

                # Escenario B: El cliente ha cambiado
                else:
                    if viejo_grabador and nuevo_grabador == viejo_grabador:
                        raise serializers.ValidationError({
                            "id_grabador_audios": "Regla de Reingreso: El Documento ha cambiado. Por seguridad anti-fraude, no puedes reutilizar el grabador de audio de la venta anterior."
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
            # REGLA 3: AUDIOS Y GRABADOR (Dependencia mutua)
            # =======================================================
            audios_data = data.get('audios')
            cantidad_audios = len(audios_data) if audios_data is not None else 0
            ya_tiene_audios = bool(self.instance.audios.all()) if self.instance else False

            if grabador:
                # 3.A: SI HAY GRABADOR
                if not ya_tiene_audios:
                    # Exigimos audios si es la primera vez
                    if cantidad_audios == 0:
                        raise serializers.ValidationError({
                            "audios": "Si asignas un Grabador, es obligatorio adjuntar los audios correspondientes."
                        })

                    # Exigimos la cantidad correcta
                    if es_dni and cantidad_audios != 12:
                        raise serializers.ValidationError({
                            "audios": f"Has asignado un grabador. Para DNI debes enviar TODOS los audios (12). Has subido {cantidad_audios}."
                        })
                    elif es_ruc and cantidad_audios != 14:
                        raise serializers.ValidationError({
                            "audios": f"Has asignado un grabador. Para RUC debes enviar TODOS los audios (14). Has subido {cantidad_audios}."
                        })
            else:
                # 3.B: SI NO HAY GRABADOR
                if cantidad_audios > 0:
                    raise serializers.ValidationError({
                        "id_grabador_audios": "No puedes adjuntar audios sin antes asignar un Grabador responsable."
                    })
        return data

    def create(self, validated_data):
        return crear_venta(
            datos_validados=validated_data,
            usuario_peticion=self.context['request'].user
        )

    def update(self, instance, validated_data):
        return actualizar_venta(
            venta=instance,
            datos_validados=validated_data,
            usuario_peticion=self.context['request'].user
        )
