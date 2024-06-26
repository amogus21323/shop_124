from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.conf.urls.static import static


from category.views import CategoryViewSet
from product.views import ProductViewSet

schema_view = get_schema_view(
    openapi.Info(
        title="Shop API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()
router.register("category", CategoryViewSet)
router.register("product", ProductViewSet)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/account/", include("account.urls")),
    path("api/order/", include("order.urls")),
    path("api/", include(router.urls)),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
