from django.urls import include, path
from rest_framework.routers import (DefaultRouter, DynamicRoute, Route,
                                    SimpleRouter)

from regional_competitions.factories import register_factory_view_sets
from regional_competitions.views import (MassSendViewSet, RankingViewSet,
                                         RegionalEventNamesRViewSet,
                                         RegionalR1MeViewSet,
                                         RegionalR1ViewSet,
                                         RegionalR4MeViewSet,
                                         RegionalR4ViewSet,
                                         RegionalR5MeViewSet,
                                         RegionalR5ViewSet,
                                         RegionalR11MeViewSet,
                                         RegionalR11ViewSet,
                                         RegionalR12MeViewSet,
                                         RegionalR12ViewSet,
                                         RegionalR13MeViewSet,
                                         RegionalR13ViewSet,
                                         RegionalR15ViewSet,
                                         RegionalR16MeViewSet,
                                         RegionalR16ViewSet,
                                         RegionalR17MeViewSet,
                                         RegionalR17ViewSet,
                                         RegionalR18MeViewSet,
                                         RegionalR18ViewSet,
                                         RegionalR19MeViewSet,
                                         RegionalR19ViewSet,
                                         RegionalR101MeViewSet,
                                         RegionalR101ViewSet,
                                         RegionalR102MeViewSet,
                                         RegionalR102ViewSet,
                                         StatisticalRegionalViewSet,
                                         r6_view_sets_factory,
                                         r9_view_sets_factory,
                                         get_sent_reports, upload_r8_data, user_info,)


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

router.register(r'ranking', RankingViewSet, basename='ranking')
router.register(r'statistical_report', StatisticalRegionalViewSet, basename='statistical_report')

router.register(r'reports/1', RegionalR1ViewSet, basename='r1')
router.register(r'reports/4', RegionalR4ViewSet, basename='r4')
router.register(r'reports/5', RegionalR5ViewSet, basename='r5')
register_factory_view_sets(
    router, 'reports/6', r6_view_sets_factory.view_set_names, r6_view_sets_factory.r_view_sets
)
# register_factory_view_sets(
#     router, 'reports/7', r7_view_sets_factory.view_set_names, r7_view_sets_factory.r_view_sets
# )
register_factory_view_sets(
    router, 'reports/9', r9_view_sets_factory.view_set_names, r9_view_sets_factory.r_view_sets
)
router.register(r'reports/10/1', RegionalR101ViewSet, basename='r10-1')
router.register(r'reports/10/2', RegionalR102ViewSet, basename='r10-2')
router.register(r'reports/11', RegionalR11ViewSet, basename='r11')
router.register(r'reports/12', RegionalR12ViewSet, basename='r12')
router.register(r'reports/13', RegionalR13ViewSet, basename='r13')
router.register(r'reports/15', RegionalR15ViewSet, basename='r15')
router.register(r'reports/16', RegionalR16ViewSet, basename='r16')
router.register(r'reports/17', RegionalR17ViewSet, basename='r17')
router.register(r'reports/18', RegionalR18ViewSet, basename='r18')
router.register(r'reports/19', RegionalR19ViewSet, basename='r19')

router.register(r'reports/event_names', RegionalEventNamesRViewSet, basename='event_names')
router.register(r'me/reports', MassSendViewSet, basename='mass_send_reports')

me_router.register(r'reports/1', RegionalR1MeViewSet, basename='r1_me')
me_router.register(r'reports/4', RegionalR4MeViewSet, basename='r4_me')
me_router.register(r'reports/5', RegionalR5MeViewSet, basename='r5_me')
register_factory_view_sets(
    me_router, 'reports/6', r6_view_sets_factory.view_set_names, r6_view_sets_factory.r_me_view_sets
)
# register_factory_view_sets(
#     me_router, 'reports/7', r7_view_sets_factory.view_set_names, r7_view_sets_factory.r_me_view_sets
# )
register_factory_view_sets(
    me_router, 'reports/9', r9_view_sets_factory.view_set_names, r9_view_sets_factory.r_me_view_sets
)
me_router.register(r'reports/10/1', RegionalR101MeViewSet, basename='r10-1_me')
me_router.register(r'reports/10/2', RegionalR102MeViewSet, basename='r10-2_me')
me_router.register(r'reports/11', RegionalR11MeViewSet, basename='r11_me')
me_router.register(r'reports/12', RegionalR12MeViewSet, basename='r12_me')
me_router.register(r'reports/13', RegionalR13MeViewSet, basename='r13_me')
me_router.register(r'reports/16', RegionalR16MeViewSet, basename='r16_me')
me_router.register(r'reports/17', RegionalR17MeViewSet, basename='r17_me')
me_router.register(r'reports/18', RegionalR18MeViewSet, basename='r18_me')
me_router.register(r'reports/19', RegionalR19MeViewSet, basename='r19_me')


urlpatterns = [
    path('', include(router.urls)),
    path('me/', include(me_router.urls)),
    path('get_sent_reports/', get_sent_reports, name='get_sent_reports'),
    path('upload_r8_data/', upload_r8_data, name='upload_r8_data'),
    path('user_info/', user_info, name='user_info'),
]
