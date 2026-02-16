from rest_framework import permissions


class EsDueño(permissions.BasePermission):
    """Acceso absoluto solo para el DUEÑO"""

    def has_permission(self, request, view):
        return bool(request.user.id_rol and request.user.id_rol.codigo == 'DUENO')


class PuedeGestionarUsuarios(permissions.BasePermission):
    """RRHH, Supervisor y Dueño pueden crear usuarios"""

    def has_permission(self, request, view):
        roles_permitidos = ['DUENO', 'SUPERVISOR', 'RRHH']
        return bool(request.user.id_rol and request.user.id_rol.codigo in roles_permitidos)


class PuedeTomarAsistencia(permissions.BasePermission):
    """RRHH y Dueño"""

    def has_permission(self, request, view):
        roles_permitidos = ['DUENO', 'RRHH']
        return bool(request.user.id_rol and request.user.id_rol.codigo in roles_permitidos)


class EsBackOfficeODueño(permissions.BasePermission):
    """Para actualizar estados de instalación, SEC y SOT"""

    def has_permission(self, request, view):
        roles_permitidos = ['DUENO', 'BACKOFFICE']
        return bool(request.user.id_rol and request.user.id_rol.codigo in roles_permitidos)


class EsPropietarioVentaODueño(permissions.BasePermission):
    """
    El Asesor solo puede ver/editar sus propias ventas.
    El Dueño, Supervisor y Backoffice pueden ver las de todos.
    """

    def has_object_permission(self, request, view, obj):
        # Si es un rol superior, lo dejamos pasar a cualquier registro
        roles_superiores = ['DUENO', 'SUPERVISOR', 'BACKOFFICE']
        if request.user.id_rol and request.user.id_rol.codigo in roles_superiores:
            return True

        # Si es un ASESOR, verificamos que el ID de la venta le pertenezca
        # (Asumiendo que el modelo Venta tiene un campo 'id_asesor')
        return obj.id_asesor == request.user


class SoloLecturaOCrearSiEsJefe(permissions.BasePermission):
    """
    Todos pueden hacer GET.
    Solo DUEÑO y SUPERVISOR pueden hacer POST, PUT, PATCH, DELETE.
    """

    def has_permission(self, request, view):
        # Si la petición es un GET, OPTIONS o HEAD (peticiones seguras), los dejamos pasar
        if request.method in permissions.SAFE_METHODS:
            return True

        # Si es un POST o DELETE, verificamos que sea jefe
        roles_jefes = ['DUENO', 'SUPERVISOR']
        return bool(request.user.id_rol and request.user.id_rol.codigo in roles_jefes)


class SoloLecturaRolesOCrearDueno(permissions.BasePermission):
    """
    Todos los empleados logueados pueden ver los roles (GET) para llenar los <select>.
    Pero solo el DUEÑO puede crear, editar o borrar roles (POST, PUT, DELETE).
    """

    def has_permission(self, request, view):
        # Si es GET, HEAD u OPTIONS (Solo lectura), pasan todos
        if request.method in permissions.SAFE_METHODS:
            return True

        # Si es escritura, verificamos que sea el DUEÑO
        return bool(request.user.id_rol and request.user.id_rol.codigo == 'DUENO')