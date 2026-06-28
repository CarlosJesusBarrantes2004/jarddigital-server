from rest_framework import serializers

# ==========================================
# CHOICES COMPARTIDOS
# ==========================================
ESTADO_SOT_CHOICES = [
    ('ATENDIDO', 'Atendido'),
    ('PENDIENTE', 'Pendiente'),
    ('RECHAZADO', 'Rechazado'),
]

MODALIDAD_CHOICES = [
    ('CALL', 'Call'),
    ('CAMPO', 'Campo'),
]

DIMENSION_CHOICES = [
    ('GEOGRAFIA', 'Geografía'),
    ('PRODUCTO', 'Producto'),
]


# ==========================================
# ENDPOINT 1 — Matriz Pivote (Gráficos 1 y 3)
# ==========================================
class MatrizPivoteInputSerializer(serializers.Serializer):
    anio = serializers.IntegerField(min_value=2020, max_value=2100)
    estado_sot = serializers.ChoiceField(choices=ESTADO_SOT_CHOICES)


# ==========================================
# ENDPOINT 2 — Barras de Rendimiento (Gráficos 2 y 4)
# ==========================================
class BarrasRendimientoInputSerializer(serializers.Serializer):
    anio = serializers.IntegerField(min_value=2020, max_value=2100)
    estado_sot = serializers.ChoiceField(choices=ESTADO_SOT_CHOICES, required=False, allow_null=True)
    mes = serializers.IntegerField(min_value=1, max_value=12, required=False, allow_null=True)
    id_asesor = serializers.IntegerField(required=False, allow_null=True)


# ==========================================
# ENDPOINT 3 — Tendencia Diaria (Gráfico 5)
# ==========================================
class TendenciaDiariaInputSerializer(serializers.Serializer):
    anio = serializers.IntegerField(min_value=2020, max_value=2100)
    mes = serializers.IntegerField(min_value=1, max_value=12)
    modalidad = serializers.ChoiceField(choices=MODALIDAD_CHOICES, required=False, allow_null=True)
    id_sede = serializers.IntegerField(required=False, allow_null=True)


# ==========================================
# ENDPOINT 4 — Árbol Jerárquico (Gráfico 6)
# ==========================================
class DistribucionJerarquicaInputSerializer(serializers.Serializer):
    estado_sot = serializers.ChoiceField(choices=ESTADO_SOT_CHOICES)
    dimension = serializers.ChoiceField(choices=DIMENSION_CHOICES)
    nivel = serializers.IntegerField(min_value=0, max_value=2)
    anio = serializers.IntegerField(min_value=2020, max_value=2100, required=False, allow_null=True)
    padre_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    solo_alto_valor = serializers.BooleanField(required=False, default=False)
    modalidad = serializers.ChoiceField(choices=MODALIDAD_CHOICES, required=False, allow_null=True)
    id_sede = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        """
        Regla cruzada: si nivel > 0, padre_id es obligatorio.
        El nivel 0 (raíz del árbol) nunca debe traer padre_id.
        """
        nivel = data.get('nivel')
        padre_id = data.get('padre_id')

        if nivel > 0 and not padre_id:
            raise serializers.ValidationError({
                "padre_id": f"El nivel {nivel} requiere un 'padre_id' del nivel anterior seleccionado."
            })

        if nivel == 0 and padre_id:
            raise serializers.ValidationError({
                "padre_id": "El nivel 0 es la raíz del árbol y no debe recibir 'padre_id'."
            })

        return data

    def validate_padre_id(self, value):
        """
        padre_id puede ser numérico (GEOGRAFIA) o texto (PRODUCTO en niveles
        campana/tipo_solucion). Lo dejamos como string y el selector decide
        cómo usarlo según la dimensión.
        """
        return value