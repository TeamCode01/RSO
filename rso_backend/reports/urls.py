from django.urls import path
from reports.views import (ReportView, SafetyTestResultsView, ExportSafetyTestResultsView, CompetitionParticipantView,
                           ExportCompetitionParticipantsResultsView)

urlpatterns = [
    path('', ReportView.as_view(), name='reports'),
    path(
        'safety_test_results/',
        SafetyTestResultsView.as_view(),
        name='safety_test_results'
    ),
    path(
        'safety_test_results/export/',
        ExportSafetyTestResultsView.as_view(),
        name='export_safety_test_results'
    ),
    path(
        'competition_participants/',
        CompetitionParticipantView.as_view(),
        name='competition_participants'
    ),
    path(
        'competition_participants/export',
        ExportCompetitionParticipantsResultsView.as_view(),
        name='export_competition_participants_results'
    )

]
