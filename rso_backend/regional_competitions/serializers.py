from rest_framework import serializers

from api.utils import create_first_or_exception
from regional_competitions.constants import STATISTICAL_REPORT_EXISTS
from regional_competitions.models import StatisticalRegionalReport


class StatisticalRegionalReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatisticalRegionalReport
        fields = (
            'id',
            'participants_number',
            'regional_headquarter',
            'employed_sso',
            'employed_spo',
            'employed_sop',
            'employed_smo',
            'employed_sservo',
            'employed_ssho',
            'employed_specialized_detachments',
            'employed_production_detachments',
            'employed_top',
        )
        read_only_fields = ('id', 'regional_headquarter')

    def create(self, validated_data):
        return create_first_or_exception(
            self,
            validated_data,
            StatisticalRegionalReport,
            STATISTICAL_REPORT_EXISTS
        )
