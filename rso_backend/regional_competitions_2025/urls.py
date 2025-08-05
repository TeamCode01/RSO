from django.urls import include, path
from regional_competitions_2025.factories import register_factory_view_sets
from regional_competitions_2025.views import (RegionalR19MeViewSet, RegionalR19ViewSet, RegionalR1MeViewSet,
                                              RegionalR1ViewSet,
                                              RegionalR2AutoViewSet,
                                              RegionalR4MeViewSet,
                                              RegionalR4ViewSet,
                                              RegionalR7AutoViewSet,
                                              RegionalR8AutoViewSet,
                                              RegionalR12MeViewSet,
                                              RegionalR12ViewSet,
                                              RegionalR13ViewSet,
                                              RegionalR17MeViewSet,
                                              RegionalR17ViewSet,
                                              RegionalR18MeViewSet,
                                              RegionalR18ViewSet, r9_view_sets_factory)
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

router.register(r'reports/1', RegionalR1ViewSet, basename='r1')
me_router.register(r'reports/1', RegionalR1MeViewSet, basename='r1_me')
router.register(r'reports/2', RegionalR2AutoViewSet, basename='r2')
router.register(r'reports/4', RegionalR4ViewSet, basename='r4')
me_router.register(r'reports/4', RegionalR4MeViewSet, basename='r4_me')
router.register(r'reports/7', RegionalR7AutoViewSet, basename='r7')
router.register(r'reports/8', RegionalR8AutoViewSet, basename='r8')
register_factory_view_sets(router, 'reports/9', r9_view_sets_factory.view_set_names, r9_view_sets_factory.r_view_sets)
router.register(r'reports/12', RegionalR12ViewSet, basename='r12')
me_router.register(r'reports/12', RegionalR12MeViewSet, basename='r12_me')
router.register(r'reports/13', RegionalR13ViewSet, basename='r13')
# router.register(r'reports/14', RegionalR14ViewSet, basename='r14')
# me_router.register(r'reports/14', RegionalR14MeViewSet, basename='r14_me')
# router.register(r'reports/16', RegionalR16ViewSet, basename='r16')
# me_router.register(r'reports/16', RegionalR16MeViewSet, basename='r16_me')
router.register(r'reports/17', RegionalR17ViewSet, basename='r17')
me_router.register(r'reports/17', RegionalR17MeViewSet, basename='r17_me')
router.register(r'reports/18', RegionalR18ViewSet, basename='r18')
me_router.register(r'reports/18', RegionalR18MeViewSet, basename='r18_me')
router.register(r'reports/19', RegionalR19ViewSet, basename='r19')
me_router.register(r'reports/19', RegionalR19MeViewSet, basename='r19_me')

urlpatterns = [
    path('', include(router.urls)),
    path('me/', include(me_router.urls)),
]
