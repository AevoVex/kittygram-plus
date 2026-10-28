from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cats.serializers import CatListSerializer

from .models import Collection, CollectionCatProposal, CollectionMember
from .permissions import (
    CanManageCollectionCats,
    CanReviewCollectionProposals,
    IsCollectionMember,
    IsCollectionOwner,
)
from .serializers import (
    CollectionCatProposalSerializer,
    CollectionCatProposalWriteSerializer,
    CollectionCatWriteSerializer,
    CollectionMemberRoleSerializer,
    CollectionMemberSerializer,
    CollectionMemberWriteSerializer,
    CollectionSerializer,
)


class CollectionViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at', 'updated_at']
    ordering = ['-updated_at', '-id']

    def get_queryset(self):
        queryset = Collection.objects.select_related('owner').prefetch_related('cats')
        if self.action == 'list':
            queryset = queryset.filter(members__user=self.request.user).prefetch_related(
                Prefetch(
                    'members',
                    queryset=CollectionMember.objects.filter(user=self.request.user),
                    to_attr='request_membership',
                )
            )
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action != 'list':
            return queryset
        role = self.request.query_params.get('role')
        if not role:
            return queryset
        allowed_roles = set(CollectionMember.Role.values)
        if role not in allowed_roles:
            raise ValidationError({
                'role': 'Допустимые значения: owner, editor, viewer.',
            })
        return queryset.filter(members__user=self.request.user, members__role=role)

    def get_permissions(self):
        if self.action in {'retrieve', 'members'} and self.request.method == 'GET':
            classes = [IsAuthenticated, IsCollectionMember]
        elif self.action in {'update', 'partial_update', 'destroy', 'member_detail'}:
            classes = [IsAuthenticated, IsCollectionOwner]
        elif self.action in {'add_cat', 'remove_cat'}:
            classes = [IsAuthenticated, CanManageCollectionCats]
        elif self.action in {'approve_proposal', 'reject_proposal'}:
            classes = [IsAuthenticated, CanReviewCollectionProposals]
        else:
            classes = [IsAuthenticated]
        if self.action == 'members' and self.request.method == 'POST':
            classes = [IsAuthenticated, IsCollectionOwner]
        if self.action == 'proposals' and self.request.method == 'GET':
            classes = [IsAuthenticated, CanReviewCollectionProposals]
        return [permission() for permission in classes]

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        collection = self.get_object()
        if request.method == 'GET':
            members = collection.members.select_related('user').all()
            return Response(CollectionMemberSerializer(members, many=True).data)

        serializer = CollectionMemberWriteSerializer(
            data=request.data,
            context={'collection': collection},
        )
        serializer.is_valid(raise_exception=True)
        member = CollectionMember.objects.create(
            collection=collection,
            **serializer.validated_data,
        )
        return Response(
            CollectionMemberSerializer(member).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['patch', 'delete'],
        url_path=r'members/(?P<user_id>[^/.]+)',
    )
    def member_detail(self, request, user_id=None, pk=None):
        collection = self.get_object()
        member = get_object_or_404(
            collection.members.select_related('user'),
            user_id=user_id,
        )
        if member.role == CollectionMember.Role.OWNER:
            raise ValidationError({
                'role': 'Нельзя изменить роль или удалить владельца подборки.',
            })
        if request.method == 'DELETE':
            member.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = CollectionMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member.role = serializer.validated_data['role']
        member.save(update_fields=['role'])
        return Response(CollectionMemberSerializer(member).data)

    @action(detail=True, methods=['post'], url_path='cats')
    def add_cat(self, request, pk=None):
        collection = self.get_object()
        serializer = CollectionCatWriteSerializer(
            data=request.data,
            context={'collection': collection, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        cat = serializer.validated_data['cat']
        collection.cats.add(cat)
        return Response(
            CatListSerializer(cat).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['delete'],
        url_path=r'cats/(?P<cat_id>[^/.]+)',
    )
    def remove_cat(self, request, cat_id=None, pk=None):
        collection = self.get_object()
        cat = get_object_or_404(collection.cats, pk=cat_id)
        collection.cats.remove(cat)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='proposals')
    def proposals(self, request, pk=None):
        collection = self.get_object()
        if request.method == 'GET':
            proposals = collection.cat_proposals.select_related(
                'cat', 'proposer', 'reviewed_by'
            ).all()
            return Response(CollectionCatProposalSerializer(proposals, many=True).data)

        serializer = CollectionCatProposalWriteSerializer(
            data=request.data,
            context={'collection': collection, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        proposal = serializer.save()
        return Response(
            CollectionCatProposalSerializer(proposal).data,
            status=status.HTTP_201_CREATED,
        )

    def _review_proposal(self, request, collection, proposal_id, decision):
        with transaction.atomic():
            proposal = get_object_or_404(
                CollectionCatProposal.objects.select_for_update(),
                collection=collection,
                pk=proposal_id,
            )
            if proposal.status != CollectionCatProposal.Status.PENDING:
                raise ValidationError({
                    'status': 'Можно рассматривать только ожидающую заявку.',
                })
            if decision == CollectionCatProposal.Status.APPROVED:
                if collection.cats.filter(pk=proposal.cat_id).exists():
                    raise ValidationError({
                        'cat_id': 'Этот котик уже есть в подборке.',
                    })
                collection.cats.add(proposal.cat)
            proposal.status = decision
            proposal.reviewed_by = request.user
            proposal.reviewed_at = timezone.now()
            proposal.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        return Response(CollectionCatProposalSerializer(proposal).data)

    @action(
        detail=True,
        methods=['post'],
        url_path=r'proposals/(?P<proposal_id>[^/.]+)/approve',
    )
    def approve_proposal(self, request, proposal_id=None, pk=None):
        collection = self.get_object()
        return self._review_proposal(
            request,
            collection,
            proposal_id,
            CollectionCatProposal.Status.APPROVED,
        )

    @action(
        detail=True,
        methods=['post'],
        url_path=r'proposals/(?P<proposal_id>[^/.]+)/reject',
    )
    def reject_proposal(self, request, proposal_id=None, pk=None):
        collection = self.get_object()
        return self._review_proposal(
            request,
            collection,
            proposal_id,
            CollectionCatProposal.Status.REJECTED,
        )
