from django.urls import include, path
from rest_framework.routers import (DefaultRouter, DynamicRoute, Route,
                                    SimpleRouter)

from regional_competitions.views import (RegionalR12MeViewSet, RegionalR12ViewSet, RegionalR13MeViewSet,
                                         RegionalR13ViewSet, RegionalR1MeViewSet, RegionalR1ViewSet, RegionalR4MeViewSet, RegionalR5MeViewSet,
                                         RegionalR4ViewSet, RegionalR5ViewSet,
                                         StatisticalRegionalViewSet, RegionalR7ViewSet, RegionalR7MeViewSet,
                                         RegionalR16ViewSet, RegionalR16MeViewSet, RegionalR101ViewSet,
                                         RegionalR102ViewSet, RegionalR101MeViewSet, RegionalR102MeViewSet,
                                         RegionalR5ViewSet, RegionalR5MeViewSet, RegionalR11ViewSet,
                                         RegionalR11MeViewSet)


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

router.register(r'reports/1', RegionalR1ViewSet, basename='r1')
router.register(r'reports/4', RegionalR4ViewSet, basename='r4')
# router.register(r'reports/5', RegionalR5ViewSet, basename='r5')
router.register(r'reports/7', RegionalR7ViewSet, basename='r7')
router.register(r'reports/10/1', RegionalR101ViewSet, basename='r10-1')
router.register(r'reports/10/2', RegionalR102ViewSet, basename='r10-2')
router.register(r'reports/12', RegionalR11ViewSet, basename='r11')
router.register(r'reports/12', RegionalR12ViewSet, basename='r12')
router.register(r'reports/13', RegionalR13ViewSet, basename='r13')
router.register(r'reports/16', RegionalR16ViewSet, basename='r16')

me_router.register(r'reports/1', RegionalR1MeViewSet, basename='r1_me')
me_router.register(r'reports/4', RegionalR4MeViewSet, basename='r4_me')
# me_router.register(r'reports/5', RegionalR5MeViewSet, basename='r5_me')
me_router.register(r'reports/7', RegionalR7MeViewSet, basename='r7_me')
me_router.register(r'reports/10/1', RegionalR101MeViewSet, basename='r10-1_me')
me_router.register(r'reports/10/2', RegionalR102MeViewSet, basename='r10-2_me')
me_router.register(r'reports/12', RegionalR11MeViewSet, basename='r11_me')
me_router.register(r'reports/12', RegionalR12MeViewSet, basename='r12_me')
me_router.register(r'reports/13', RegionalR13MeViewSet, basename='r13_me')
me_router.register(r'reports/16', RegionalR16MeViewSet, basename='r16_me')

urlpatterns = [
    path('', include(router.urls)),
    path('me/', include(me_router.urls)),
]
