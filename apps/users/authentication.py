from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CustomCookieJWTAuthentication(JWTAuthentication):
    """
    Autenticación personalizada que busca el Token en las Cookies HTTPOnly
    si no lo encuentra en la cabecera 'Authorization'.
    """

    def authenticate(self, request):
        # 1. Intentar el método clásico (Authorization: Bearer ...)
        header = self.get_header(request)

        if header is None:
            # 2. Si no hay cabecera, ¡Búscalo en la Cookie!
            raw_token = request.COOKIES.get(settings.AUTH_COOKIE) or None
        else:
            # Si sí hay cabecera, saca el token de ahí
            raw_token = self.get_raw_token(header)

        # Si no encontró el token ni en pintura, rechaza la petición
        if raw_token is None:
            return None

        # 3. Validar que el token sea real y no esté vencido
        validated_token = self.get_validated_token(raw_token)

        # 4. Devolver el usuario logueado
        return self.get_user(validated_token), validated_token

class CustomCookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    # Apuntamos a la clase que creamos hoy
    target_class = 'apps.users.authentication.CustomCookieJWTAuthentication'
    name = 'cookieAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'cookie',
            'name': 'access_token', # El nombre de tu cookie
            'description': 'Autenticación mediante Cookie HttpOnly'
        }