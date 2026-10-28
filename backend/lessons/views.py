from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Cat, Owner
from .serializers import CatSerializer, HexCatSerializer, InitialCatSerializer, OwnerSerializer


@api_view(['GET', 'POST'])
def cat_list(request):
    if request.method == 'POST':
        serializer = InitialCatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(InitialCatSerializer(Cat.objects.all(), many=True).data)


@api_view(['GET', 'POST'])
def bulk_cat_list(request):
    if request.method == 'POST':
        serializer = InitialCatSerializer(data=request.data, many=True, allow_empty=False)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(InitialCatSerializer(Cat.objects.all(), many=True).data)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def cat_detail(request, pk):
    cat = get_object_or_404(Cat, pk=pk)
    if request.method == 'GET':
        return Response(InitialCatSerializer(cat).data)
    if request.method == 'DELETE':
        cat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = InitialCatSerializer(cat, data=request.data, partial=request.method == 'PATCH')
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


class APICat(APIView):
    def get(self, request):
        return Response(InitialCatSerializer(Cat.objects.all(), many=True).data)

    def post(self, request):
        serializer = InitialCatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CatList(generics.ListCreateAPIView):
    queryset = Cat.objects.all()
    serializer_class = InitialCatSerializer


class CatDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Cat.objects.all()
    serializer_class = InitialCatSerializer


class CatViewSet(viewsets.ModelViewSet):
    queryset = Cat.objects.select_related('owner').all()
    serializer_class = CatSerializer


class HexCatViewSet(CatViewSet):
    serializer_class = HexCatSerializer


class OwnerViewSet(viewsets.ModelViewSet):
    queryset = Owner.objects.prefetch_related('cats').order_by('pk')
    serializer_class = OwnerSerializer


class ReadOnlyCatViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response(CatSerializer(Cat.objects.select_related('owner'), many=True).data)

    def retrieve(self, request, pk=None):
        cat = get_object_or_404(Cat.objects.select_related('owner'), pk=pk)
        return Response(CatSerializer(cat).data)
