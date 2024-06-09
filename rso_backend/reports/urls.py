from django.urls import path

from reports.views import (AttributesOfUniformDataView, CommanderSchoolView, CompetitionParticipantView,
                           DetachmentQResultsView, ExportAttributesOfUniformView,
                           ExportCommanderSchoolDataView,
                           ExportCompetitionParticipantsContactData,
                           ExportCompetitionParticipantsDataView,
                           ExportDetachmentQResultsView,
                           ExportMembershipFeeDataView, 
                           ExportRegionsUserDataView,
                           ExportSafetyTestResultsView, MembershipFeeDataView, ReportView,
                           SafetyTestResultsView, TaskStatusView, ExportQ5DataView)

urlpatterns = [
    path('', ReportView.as_view(), name='reports'),
    path('task-status/<str:task_id>/', TaskStatusView.as_view(), name='task_status'),
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
        'competition_participants/export/',
        ExportCompetitionParticipantsDataView.as_view(),
        name='export_competition_participants_results'
    ),
    path(
        'detachment_q_results/',
        DetachmentQResultsView.as_view(),
        name='detachment_q_results'
    ),
    path(
        'detachment_q_results/export/',
        ExportDetachmentQResultsView.as_view(),
        name='export_detachment_q_results'
    ),
    path(
        'competition_participants/contact_data/export/',
        ExportCompetitionParticipantsContactData.as_view(),
        name='competition_participants_contact_data'
    ),
    path(
        'users_data_by_regions/',
        ExportRegionsUserDataView.as_view(),
        name='regions_users_data'
    ),
    path(
        'commander_shool/export/',
        ExportCommanderSchoolDataView.as_view(),
        name='export_commander_school_results'
    ),
    path(
        'commander_shool/',
        CommanderSchoolView.as_view(),
        name='commander_school'
    ),
    path(
        'get_q5_data/export/',
        ExportQ5DataView.as_view(),
        name='export_q5_data'
    ),
    path(
        'membership_fee/export/',
        ExportMembershipFeeDataView.as_view(),
        name='membership_fee_export'
    ),
    path(
        'membership_fee/',
        MembershipFeeDataView.as_view(),
        name='membership_fee'
    ),
    path('attributes_of_uniform/export/',
         ExportAttributesOfUniformView.as_view(),
         name='attributes_of_uniform_export'),
    path(
        'attributes_of_uniform/',
        AttributesOfUniformDataView.as_view(),
        name='attributes_of_uniform'
    ),
]
