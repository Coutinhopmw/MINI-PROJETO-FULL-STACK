from django.contrib.auth import login as iniciar_sessao
from django.contrib.auth import logout as encerrar_sessao
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import LoginSerializer, UsuarioSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    @extend_schema(request=LoginSerializer, responses={200: UsuarioSerializer})
    def post(self, request):
        # Sem sessão prévia, o DRF não checa CSRF sozinho; no login exigimos explicitamente.
        SessionAuthentication().enforce_csrf(request)

        serializador = LoginSerializer(data=request.data, context={'request': request})
        serializador.is_valid(raise_exception=True)
        usuario = serializador.validated_data['usuario']

        iniciar_sessao(request, usuario)
        return Response(UsuarioSerializer(usuario).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        encerrar_sessao(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UsuarioSerializer})
    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)