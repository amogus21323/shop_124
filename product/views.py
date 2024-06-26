from django.core.cache import cache
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from rating.serializers import RatingSerializer
from .models import Product
from rest_framework import permissions
from rest_framework.decorators import action

from .permissons import IsAuthor
from .serializers import ProductSerializer
from django_filters import rest_framework as filters
from category.models import Category
from django_filters.rest_framework import DjangoFilterBackend


class ProductFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    category = filters.ModelChoiceFilter(queryset=Category.objects.all())


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter

    def perform_create(self, serializer):
        cache.delete("product_list")
        serializer.save(owner=self.request.user)

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return (IsAuthor(),)
        return (permissions.IsAuthenticatedOrReadOnly(),)

    def list(self, request, *args, **kwargs):
        cache_key = "product_list"
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response, 60 * 15)  # 15 минут
        return response

    @action(["GET", "POST", "DELETE"], detail=True)
    def ratings(self, request, pk):
        product = self.get_object()
        user = request.user
        if request.method == "GET":
            rating = product.ratings.all()
            serializer = RatingSerializer(instance=rating, many=True)
            return Response(serializer.data, status=200)
        elif request.method == "POST":
            if product.ratings.filter(owner=user).exists():
                return Response("Ты уже поставил рейтинг на этот товар", status=400)
            serializer = RatingSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(owner=user, product=product)
            return Response(serializer.data, status=201)
        else:
            if not product.ratings.filter(owner=user).exists():
                return Response(
                    "Ты не можешь удалить, потому что ты не оставлял оценку на этот товар",
                    status=400,
                )
            rating = product.ratings.get(owner=user)
            rating.delete()
            return Response("Успешно удалено", status=204)
