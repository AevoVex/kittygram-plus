"""Exercise endpoints, loaded only with config.lesson_settings."""
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('cats', views.CatViewSet, basename='lesson-cat')
router.register('owners', views.OwnerViewSet)
router.register('hex-cats', views.HexCatViewSet, basename='hex-cat')
router.register('readonly-cats', views.ReadOnlyCatViewSet, basename='readonly-cat')
urlpatterns = [
    path('functions/cats/', views.cat_list),
    path('functions/cats/<int:pk>/', views.cat_detail),
    path('bulk/cats/', views.bulk_cat_list),
    path('apiview/cats/', views.APICat.as_view()),
    path('generics/cats/', views.CatList.as_view()),
    path('generics/cats/<int:pk>/', views.CatDetail.as_view()),
    path('api-token-auth/', obtain_auth_token),
    path('', include(router.urls)),
]
