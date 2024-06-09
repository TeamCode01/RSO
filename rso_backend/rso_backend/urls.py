import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView,
                                            TokenVerifyView)

swagger_url = os.getenv('SWAGGER_URL')

if swagger_url:
    schema_view = get_schema_view(
       openapi.Info(
          title="RSO API",
          default_version='v1',
          description="Documentation",
          terms_of_service="https://www.google.com/policies/terms/",
          contact=openapi.Contact(email="rso.login@yandex.ru"),
          license=openapi.License(name="BSD License"),
       ),
       public=True,
       permission_classes=(permissions.AllowAny,),
       url=swagger_url
    )
else:
    schema_view = get_schema_view(
       openapi.Info(
          title="RSO API",
          default_version='v1',
          description="Documentation",
          terms_of_service="https://www.google.com/policies/terms/",
          contact=openapi.Contact(email="rso.login@yandex.ru"),
          license=openapi.License(name="BSD License"),
       ),
       public=True,
       permission_classes=(permissions.AllowAny,),
    )

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('rest_framework_social_oauth2.urls', namespace='authorize')),
    path('api/v1/', include('api.urls')),
    path('api/v1/', include('djoser.urls')),
    path('api/v1/', include('djoser.urls.jwt')),
    path('api/v1/', include('djoser.urls.authtoken')),
    # path(
    #     'api/v1/jwt_token/',
    #     TokenObtainPairView.as_view(),
    #     name='token_obtain_pair'
    # ),
    # path(
    #     'api/v1/jwt_token/refresh/',
    #     TokenRefreshView.as_view(),
    #     name='token_refresh'
    # ),
    # path('api/v1/jwt_token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path(
        'swagger<format>/',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json'
    ),
    path(
        'swagger/',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui'
    ),
    path(
        'redoc/',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc'
    ),
    path('accounts/', include('django.contrib.auth.urls')),
    path('reports/', include('reports.urls')),
    path('', include('headquarters.urls')),
    path('', include('events.urls')),
    path('', include('users.urls')),
    path('', include('competitions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
