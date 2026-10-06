from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from app.accounts.models import Usuario


class UsuarioResumoSerializer(serializers.ModelSerializer):
    nome = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ('id', 'username', 'nome')

    def get_nome(self, usuario) -> str:
        return usuario.first_name or usuario.username


class UsuarioSerializer(UsuarioResumoSerializer):
    perfil_display = serializers.CharField(source='get_perfil_display', read_only=True)

    class Meta(UsuarioResumoSerializer.Meta):
        fields = ('id', 'username', 'nome', 'perfil', 'perfil_display')


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, dados):
        usuario = authenticate(
            request=self.context.get('request'),
            username=dados['username'],
            password=dados['password'],
        )
        if usuario is None:  # inclui usuário inativo; a mensagem não revela qual dado errou
            raise AuthenticationFailed()
        dados['usuario'] = usuario
        return dados