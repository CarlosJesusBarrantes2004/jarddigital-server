from rest_framework import permissions

class SoloLecturaModificarJefaturas(permissions.BasePermission):
    """
    Todos los empleados logueados pueden hacer GET (ver sucursales y modalidades).
    Solo DUEÑO y SUPERVISOR pueden hacer POST, PUT, PATCH, DELETE.
    """
    def has_permission(self, request, view):
        # Si es una petición segura (GET, HEAD, OPTIONS), todos pasan
        if request.method in permissions.SAFE_METHODS:
            return True

        # Si alguien intenta crear o borrar, verificamos su placa de jefe
        roles_permitidos = ['DUENO', 'SUPERVISOR']
        return bool(request.user.id_rol and request.user.id_rol.codigo in roles_permitidos)