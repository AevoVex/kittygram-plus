import datetime as dt
import webcolors
from rest_framework import serializers
from .models import Cat, Owner


class InitialCatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cat
        fields = ('name', 'color', 'birth_year')


class CatSerializer(InitialCatSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        source='owner', queryset=Owner.objects.all(), required=False, allow_null=True, write_only=True,
    )
    age = serializers.SerializerMethodField()

    class Meta(InitialCatSerializer.Meta):
        fields = ('id', 'name', 'color', 'birth_year', 'owner', 'owner_id', 'age')

    def get_age(self, obj):
        return None if obj.birth_year is None else dt.date.today().year - obj.birth_year


class OwnerSerializer(serializers.ModelSerializer):
    cats = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Owner
        fields = ('id', 'first_name', 'last_name', 'cats')


class Hex2NameColor(serializers.Field):
    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError('Ожидается строка с hex-кодом цвета.')
        try:
            return webcolors.hex_to_name(data)
        except (ValueError, TypeError):
            raise serializers.ValidationError('Для этого цвета нет имени.')


class HexCatSerializer(CatSerializer):
    color = Hex2NameColor()
