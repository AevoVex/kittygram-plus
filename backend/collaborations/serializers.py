from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from cats.models import Cat
from cats.serializers import CatListSerializer

from .models import Collection, CollectionCatProposal, CollectionMember


User = get_user_model()


class CollectionMemberSerializer(serializers.ModelSerializer):
    user = serializers.IntegerField(source='user_id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = CollectionMember
        fields = ('user', 'username', 'role', 'created_at')
        read_only_fields = fields


class CollectionSerializer(serializers.ModelSerializer):
    owner = serializers.IntegerField(source='owner_id', read_only=True)
    my_role = serializers.SerializerMethodField()
    cats = CatListSerializer(many=True, read_only=True)
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = (
            'id', 'title', 'description', 'owner', 'my_role', 'cats',
            'members_count', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'owner', 'my_role', 'cats', 'members_count', 'created_at',
            'updated_at',
        )

    def validate_title(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError(
                'Название подборки должно содержать минимум 3 символа.'
            )
        return value

    def validate(self, attrs):
        request = self.context['request']
        title = attrs.get('title', getattr(self.instance, 'title', None))
        owner = self.instance.owner if self.instance else request.user
        duplicates = Collection.objects.filter(owner=owner, title=title)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError({
                'title': 'У вас уже есть подборка с таким названием.',
            })
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        try:
            with transaction.atomic():
                collection = Collection.objects.create(
                    owner=request.user,
                    **validated_data,
                )
                CollectionMember.objects.create(
                    collection=collection,
                    user=request.user,
                    role=CollectionMember.Role.OWNER,
                )
                return collection
        except IntegrityError:
            raise serializers.ValidationError({
                'title': 'У вас уже есть подборка с таким названием.',
            })

    def get_my_role(self, obj):
        memberships = getattr(obj, 'request_membership', ())
        if memberships:
            return memberships[0].role
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        membership = CollectionMember.objects.filter(
            collection=obj,
            user=request.user,
        ).only('role').first()
        return membership.role if membership else None

    def get_members_count(self, obj):
        return obj.members.count()


class CollectionMemberWriteSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
    )
    role = serializers.ChoiceField(
        choices=[
            CollectionMember.Role.EDITOR,
            CollectionMember.Role.VIEWER,
        ],
    )

    def validate_user_id(self, user):
        collection = self.context['collection']
        if CollectionMember.objects.filter(collection=collection, user=user).exists():
            raise serializers.ValidationError('Этот пользователь уже участвует в подборке.')
        return user


class CollectionMemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            CollectionMember.Role.EDITOR,
            CollectionMember.Role.VIEWER,
        ],
    )


class CollectionCatWriteSerializer(serializers.Serializer):
    cat_id = serializers.PrimaryKeyRelatedField(queryset=Cat.objects.all(), source='cat')

    def validate_cat_id(self, cat):
        collection = self.context['collection']
        request = self.context['request']
        if cat.owner_id != request.user.id:
            raise PermissionDenied(
                'Добавлять можно только котиков, принадлежащих вам.'
            )
        if collection.cats.filter(pk=cat.pk).exists():
            raise serializers.ValidationError('Этот котик уже добавлен в подборку.')
        return cat


class CollectionCatProposalSerializer(serializers.ModelSerializer):
    cat = CatListSerializer(read_only=True)
    proposer = serializers.IntegerField(source='proposer_id', read_only=True)
    proposer_username = serializers.CharField(source='proposer.username', read_only=True)
    reviewed_by = serializers.IntegerField(source='reviewed_by_id', read_only=True)
    reviewed_by_username = serializers.CharField(
        source='reviewed_by.username',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = CollectionCatProposal
        fields = (
            'id', 'cat', 'proposer', 'proposer_username', 'status', 'reviewed_by',
            'reviewed_by_username', 'created_at', 'reviewed_at',
        )
        read_only_fields = fields


class CollectionCatProposalWriteSerializer(serializers.Serializer):
    cat_id = serializers.PrimaryKeyRelatedField(queryset=Cat.objects.all(), source='cat')

    def validate_cat_id(self, cat):
        collection = self.context['collection']
        request = self.context['request']
        if cat.owner_id != request.user.id:
            raise PermissionDenied(
                'Предлагать можно только котиков, принадлежащих вам.'
            )
        if collection.cats.filter(pk=cat.pk).exists():
            raise serializers.ValidationError('Этот котик уже есть в подборке.')
        if CollectionCatProposal.objects.filter(collection=collection, cat=cat).exists():
            raise serializers.ValidationError(
                'Заявка на добавление этого котика уже существует.'
            )
        return cat

    def create(self, validated_data):
        request = self.context['request']
        collection = self.context['collection']
        try:
            with transaction.atomic():
                return CollectionCatProposal.objects.create(
                    collection=collection,
                    proposer=request.user,
                    **validated_data,
                )
        except IntegrityError:
            raise serializers.ValidationError({
                'cat_id': 'Заявка на добавление этого котика уже существует.',
            })
