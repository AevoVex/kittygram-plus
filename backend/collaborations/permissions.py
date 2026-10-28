from rest_framework.permissions import BasePermission

from .models import CollectionMember


class IsCollectionMember(BasePermission):
    message = 'Вы не состоите в этой подборке.'

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and CollectionMember.objects.filter(collection=obj, user=request.user).exists()
        )


class IsCollectionOwner(BasePermission):
    message = 'Только владелец подборки может выполнить это действие.'

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and obj.owner_id == request.user.id
        )


class CanManageCollectionCats(BasePermission):
    message = 'Только владелец или редактор может изменять состав подборки.'

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and CollectionMember.objects.filter(
                collection=obj,
                user=request.user,
                role__in=[CollectionMember.Role.OWNER, CollectionMember.Role.EDITOR],
            ).exists()
        )


class CanReviewCollectionProposals(BasePermission):
    message = 'Только владелец или редактор может рассматривать заявки.'

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and CollectionMember.objects.filter(
                collection=obj,
                user=request.user,
                role__in=[CollectionMember.Role.OWNER, CollectionMember.Role.EDITOR],
            ).exists()
        )
