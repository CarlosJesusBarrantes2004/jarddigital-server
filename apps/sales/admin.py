from django.contrib import admin
from .models import Venta, Producto, EstadoSOT


# El decorador @admin.register le avisa a Django que prepare este modelo
@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    # list_display: ¿Qué columnas quieres ver en la tabla principal?
    list_display = ('id', 'cliente_nombre', 'cliente_numero_doc', 'tipo_venta', 'fecha_creacion')

    # search_fields: Agrega una barra de búsqueda para encontrar por estos campos
    search_fields = ('cliente_numero_doc', 'cliente_nombre', 'codigo_sot')

    # list_filter: Agrega un menú lateral para filtrar rápidamente
    list_filter = ('tipo_venta', 'fecha_creacion')

    # readonly_fields: Protege los campos que nadie debería editar a mano
    readonly_fields = ('fecha_creacion', 'usuario_creacion')


# Puedes registrar modelos más simples con menos configuración:
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre_paquete', 'tipo_solucion', 'costo_fijo_plan', 'activo')
    list_filter = ('activo', 'tipo_solucion')


@admin.register(EstadoSOT)
class EstadoSOTAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'orden', 'activo')