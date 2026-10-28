from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from cats.views import AchievementViewSet, CatViewSet, LightCatViewSet, UserViewSet
from collaborations.views import CollectionViewSet

router = DefaultRouter()
router.register('cats', CatViewSet)
router.register('users', UserViewSet)
router.register('achievements', AchievementViewSet)
router.register('mycats', LightCatViewSet, basename='light-cat')
router.register('collections', CollectionViewSet, basename='collection')
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/', include('djoser.urls')),
    path('api/', include('djoser.urls.authtoken')),
    path('api/token/', include('djoser.urls.authtoken')),
    path('api/users/', include('djoser.urls')),
    path('api/', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
