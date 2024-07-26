from django.contrib import admin

from regional_competitions.models import StatisticalRegionalReport


@admin.register(StatisticalRegionalReport)
class StatisticalRegionalReportAdmin(admin.ModelAdmin):
    list_display = (
        'regional_headquarter',
        'participants_number',
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
    search_fields = (
        'regional_headquarter__name',
        'regional_headquarter__id',
    )
