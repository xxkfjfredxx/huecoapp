from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

class VersionedJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        token_ver = int(validated_token.get("ver", 0))
        current_ver = int(getattr(user, "token_version", 0))
        if token_ver != current_ver:
            raise AuthenticationFailed("Token invalidated by a newer login")
        return user
