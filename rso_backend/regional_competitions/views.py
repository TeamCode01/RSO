from rest_framework import permissions

from api.mixins import CreateViewSet
from headquarters.models import RegionalHeadquarter
from regional_competitions.permissions import IsRegionalCommander
from regional_competitions.models import StatisticalRegionalReport
from regional_competitions.serializers import \
    StatisticalRegionalReportSerializer


class StatisticalRegionalViewSet(CreateViewSet):
    queryset = StatisticalRegionalReport.objects.all()
    permission_classes = (permissions.IsAuthenticated, IsRegionalCommander,)
    serializer_class = StatisticalRegionalReportSerializer

    def perform_create(self, serializer):
        regional_headquarter = RegionalHeadquarter.objects.get(
            commander=self.request.user
        )
        serializer.save(regional_headquarter=regional_headquarter)
