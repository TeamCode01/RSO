from django.urls import include, path
from regional_competitions_2025.views import RegionalR4MeViewSet, RegionalR4ViewSet
from rest_framework.routers import (DefaultRouter, DynamicRoute, Route,
                                    SimpleRouter)


class MeRouter(SimpleRouter):
    """Роутер, генерирующий корректные урлы для /me вьюсетов."""
    routes = [
        Route(
            url=r'^{prefix}/all$',
            mapping={
                'get': 'list',
                # 'post': 'create'
            },
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
        Route(
            url=r'^{prefix}/$',
            mapping={
                'get': 'retrieve',
                'put': 'update',
                'delete': 'destroy'
            },
            name='{basename}-detail',
            detail=True,
            initkwargs={'suffix': 'Detail'}
        ),
        DynamicRoute(
            url=r'^{prefix}/{url_path}$',
            name='{basename}-{url_name}',
            detail=True,
            initkwargs={}
        )
    ]


me_router = MeRouter()
router = DefaultRouter()

router.register(r'reports/4', RegionalR4ViewSet, basename='r4')
me_router.register(r'reports/4', RegionalR4MeViewSet, basename='r4_me')

urlpatterns = [
    path('', include(router.urls)),
    path('me/', include(me_router.urls)),
]
