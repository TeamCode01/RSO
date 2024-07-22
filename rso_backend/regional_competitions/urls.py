from django.urls import include, path
from rest_framework.routers import (DefaultRouter, DynamicRoute, Route,
                                    SimpleRouter)

from regional_competitions.views import (RegionalR4MeViewSet,
                                         RegionalR4ViewSet,
                                         StatisticalRegionalViewSet, RegionalR7ViewSet, RegionalR7MeViewSet)


class MeRouter(SimpleRouter):
    """Роутер, генерирующий корректные урлы для /me вьюсетов."""
    routes = [
        Route(
            url=r'^{prefix}/all$',
            mapping={
                'get': 'list',
                'post': 'create'
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

router.register(r'statistical_report', StatisticalRegionalViewSet, basename='statistical_report')

router.register(r'reports/4', RegionalR4ViewSet, basename='r4')
router.register(r'reports/7', RegionalR7ViewSet, basename='r7')

me_router.register(r'reports/4', RegionalR4MeViewSet, basename='r4_me')
me_router.register(r'reports/7', RegionalR7MeViewSet, basename='r7_me')

urlpatterns = [
    path('', include(router.urls)),
    path('me/', include(me_router.urls)),
]
