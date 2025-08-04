from django.urls import include, path
from regional_competitions_2025.views import RegionalR4MeViewSet, RegionalR4ViewSet, RegionalR7AutoViewSet, RegionalR13ViewSet, RegionalR14ViewSet, RegionalR16ViewSet, RegionalR17ViewSet, RegionalR18ViewSet, RegionalR14MeViewSet, RegionalR16MeViewSet, RegionalR17MeViewSet, RegionalR18MeViewSet
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
router.register(r'reports/7', RegionalR7AutoViewSet, basename='r7')
router.register(r'reports/13', RegionalR13ViewSet, basename='r13')
router.register(r'reports/14', RegionalR14ViewSet, basename='r14')
me_router.register(r'reports/14', RegionalR14MeViewSet, basename='r14_me')
router.register(r'reports/16', RegionalR16ViewSet, basename='r16')
me_router.register(r'reports/16', RegionalR16MeViewSet, basename='r16_me')
router.register(r'reports/17', RegionalR17ViewSet, basename='r17')
me_router.register(r'reports/17', RegionalR17MeViewSet, basename='r17_me')
router.register(r'reports/18', RegionalR18ViewSet, basename='r18')
me_router.register(r'reports/18', RegionalR18MeViewSet, basename='r18_me')

urlpatterns = [
    path('', include(router.urls)),
    path('me/', include(me_router.urls)),
]
