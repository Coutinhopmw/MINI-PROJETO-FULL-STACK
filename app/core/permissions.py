from rest_framework.permissions import BasePermission


class EhAtendente(BasePermission):
    message = 'Apenas atendentes podem executar esta ação.'

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.eh_atendente)


class EhSolicitante(BasePermission):
    message = 'Apenas quem abriu a solicitação pode executar esta ação.'

    def has_object_permission(self, request, view, obj):
        return obj.solicitante_id == request.user.id