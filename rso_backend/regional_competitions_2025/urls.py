from django.urls import include, path
from regional_competitions_2025.factories import register_factory_view_sets
from regional_competitions_2025.views import (MassSendViewSet, RankingViewSet, RegionalEventNamesRViewSet, RegionalR1MeViewSet, RegionalR1ViewSet, RegionalR2AutoViewSet,
                                              RegionalR3ViewSet, RegionalR3MeViewSet, RegionalR4MeViewSet, RegionalR4ViewSet, RegionalR5ViewSet, RegionalR5MeViewSet,RegionalR7AutoViewSet,
                                              RegionalR8AutoViewSet, RegionalR101MeViewSet, RegionalR101ViewSet,RegionalR102MeViewSet, RegionalR102ViewSet, RegionalR11MeViewSet, RegionalR11ViewSet, RegionalR12MeViewSet, RegionalR12ViewSet,
                                              RegionalR13ViewSet, RegionalR14MeViewSet, RegionalR14ViewSet, RegionalR16MeViewSet, RegionalR16ViewSet, RegionalR17MeViewSet, RegionalR17ViewSet, RegionalR18MeViewSet, RegionalR18ViewSet, RegionalR19MeViewSet,RegionalR19ViewSet, RegionalR20MeViewSet, RegionalR20ViewSet, RegionalR15ViewSet, StatisticalRegionalViewSet, download_mass_reports_xlsx, get_sent_reports,
                                              r9_view_sets_factory, r6_view_sets_factory, upload_r8_data, user_info)
from rest_framework.routers import DefaultRouter, DynamicRoute, Route, SimpleRouter


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
me_router.register(r'reports/1', RegionalR1MeViewSet, basename='r1_me')
router.register(r'reports/2', RegionalR2AutoViewSet, basename='r2')
router.register(r'reports/3', RegionalR3ViewSet, basename='r3')
me_router.register(r'reports/3', RegionalR3MeViewSet, basename='r3_me')
router.register(r'reports/4', RegionalR4ViewSet, basename='r4')
me_router.register(r'reports/4', RegionalR4MeViewSet, basename='r4_me')
router.register(r'reports/5', RegionalR5ViewSet, basename='r5')
me_router.register(r'reports/5', RegionalR5MeViewSet, basename='r5_me')
register_factory_view_sets(
    router, 'reports/6', r6_view_sets_factory.view_set_names, r6_view_sets_factory.r_view_sets
)
register_factory_view_sets(
    me_router, 'reports/6', r6_view_sets_factory.view_set_names, r6_view_sets_factory.r_me_view_sets
    )
router.register(r'reports/7', RegionalR7AutoViewSet, basename='r7')
router.register(r'reports/8', RegionalR8AutoViewSet, basename='r8')
register_factory_view_sets(router, 'reports/9', r9_view_sets_factory.view_set_names, r9_view_sets_factory.r_view_sets)
router.register(r'reports/10/1', RegionalR101ViewSet, basename='r10-1')
router.register(r'reports/10/2', RegionalR102ViewSet, basename='r10-2')
me_router.register(r'reports/10/1', RegionalR101MeViewSet, basename='r10-1_me')
me_router.register(r'reports/10/2', RegionalR102MeViewSet, basename='r10-2_me')
router.register(r'reports/11', RegionalR11ViewSet, basename='r11')
me_router.register(r'reports/11', RegionalR11MeViewSet, basename='r11_me')
router.register(r'reports/12', RegionalR12ViewSet, basename='r12')
me_router.register(r'reports/12', RegionalR12MeViewSet, basename='r12_me')
router.register(r'reports/13', RegionalR13ViewSet, basename='r13')
router.register(r'reports/14', RegionalR14ViewSet, basename='r14')
me_router.register(r'reports/14', RegionalR14MeViewSet, basename='r14_me')
router.register(r'reports/15', RegionalR15ViewSet, basename='r15')
router.register(r'reports/16', RegionalR16ViewSet, basename='r16')
me_router.register(r'reports/16', RegionalR16MeViewSet, basename='r16_me')
router.register(r'reports/17', RegionalR17ViewSet, basename='r17')
me_router.register(r'reports/17', RegionalR17MeViewSet, basename='r17_me')
router.register(r'reports/18', RegionalR18ViewSet, basename='r18')
me_router.register(r'reports/18', RegionalR18MeViewSet, basename='r18_me')
router.register(r'reports/19', RegionalR19ViewSet, basename='r19')
me_router.register(r'reports/19', RegionalR19MeViewSet, basename='r19_me')
router.register(r'reports/20', RegionalR20ViewSet, basename='r20')
me_router.register(r'reports/20', RegionalR20MeViewSet, basename='r20_me')


router.register(r'reports/event_names', RegionalEventNamesRViewSet, basename='event_names')
router.register(r'me/reports', MassSendViewSet, basename='mass_send_reports')

urlpatterns = [
    path('', include(router.urls)),
    path('me/', include(me_router.urls)),
    path('get_sent_reports/', get_sent_reports, name='get_sent_reports'),
    path('upload_r8_data/', upload_r8_data, name='upload_r8_data'),
    path('user_info/', user_info, name='user_info'),
    path('<int:pk>/download_mass_reports_xlsx/', download_mass_reports_xlsx, name='download_mass_reports_xlsx'),
]