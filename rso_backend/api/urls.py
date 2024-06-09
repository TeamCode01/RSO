from django.urls import include, path
from djoser.views import UserViewSet
from rest_framework.routers import DefaultRouter

from api.constants import (CREATE_DELETE, CREATE_METHOD, DELETE,
                           DELETE_UPDATE_RETRIEVE, DOWNLOAD_ALL_FORMS,
                           DOWNLOAD_CONSENT_PD, DOWNLOAD_MEMBERSHIP_FILE,
                           DOWNLOAD_PARENT_CONSENT_PD, EXCHANGE_TOKEN, LIST,
                           POST_RESET_PASSWORD, RETRIEVE_CREATE, UPDATE_DELETE,
                           UPDATE_RETRIEVE, LIST_CREATE,)
from api.views import (AreaViewSet, EducationalInstitutionViewSet,
                       MemberCertViewSet, RegionViewSet,
                       ExchangeTokenView, VKLoginAPIView,
                       change_membership_fee_status, verify_user)
from competitions.views import (CompetitionApplicationsViewSet,
                                CompetitionParticipantsViewSet,
                                CompetitionViewSet,
                                DetachmentCompetitionIsTandemView,
                                Q2DetachmentReportViewSet,
                                Q5DetachmentReportViewSet,
                                Q5EducatedParticipantViewSet,
                                Q6DetachmentReportViewSet,
                                Q7UpdateDestroyViewSet, Q7ViewSet,
                                Q8UpdateDestroyViewSet, Q8ViewSet,
                                Q9UpdateDestroyViewSet, Q9ViewSet,
                                Q10UpdateDestroyViewSet, Q10ViewSet,
                                Q11UpdateDestroyViewSet, Q11ViewSet,
                                Q12UpdateDestroyViewSet, Q12ViewSet,
                                Q13DetachmentReportViewSet,
                                Q13EventOrganizationViewSet,
                                Q14DetachmentReportViewSet,
                                Q14LaborProjectViewSet,
                                Q15DetachmentReportViewSet,
                                Q15GrantDataViewSet, Q16ViewSet,
                                Q17DetachmentReportViewSet,
                                Q17EventLinkViewSet,
                                Q18DetachmentReportViewSet,
                                Q19DetachmentReportViewset, Q20ViewSet,
                                QVerificationLogByNumberView,
                                get_detachment_place, get_detachment_places,
                                get_place_overall, get_place_q1, get_place_q3,
                                get_place_q4, get_q1_info)
from events.views import (AnswerDetailViewSet, EventAdditionalIssueViewSet,
                          EventApplicationsViewSet,
                          EventOrganizationDataViewSet,
                          EventParticipantsViewSet, EventUserDocumentViewSet,
                          EventViewSet, GroupEventApplicationViewSet,
                          MultiEventViewSet, create_answers,
                          group_applications, group_applications_me,
                          is_participant_or_applicant)
from headquarters.views import (#CentralAcceptViewSet,
                                DetachmentAcceptViewSet,
                                DetachmentApplicationViewSet,
                                DetachmentPositionViewSet, DetachmentViewSet,
                                DistrictPositionViewSet, DistrictViewSet,
                                EducationalPositionViewSet, EducationalViewSet,
                                LocalPositionViewSet, LocalViewSet,
                                PositionViewSet, #RegionalAcceptViewSet,
                                RegionalViewSet, #RegionalApplicationViewSet,
                                #CentralApplicationViewSet,
                                CentralPositionViewSet, # LocalAcceptViewSet,
                                CentralViewSet,  #DistrictAcceptViewSet,
                                #DistrictApplicationViewSet,
                                RegionalPositionViewSet,
                                # LocalApplicationViewSet,
                                # EducationalAcceptViewSet,
                                # EducationalApplicationViewSet,
                                get_structural_units)
from questions.views import QuestionsView, get_attempts_status, submit_answers
from users.views import (AdditionalForeignDocsViewSet, CustomUserViewSet,
                         ForeignUserDocumentsViewSet, RSOUserViewSet,
                         SafeUserViewSet, UserDocumentsViewSet,
                         UserEducationViewSet, UserForeignParentDocsViewSet,
                         UserMediaViewSet, UserPrivacySettingsViewSet,
                         UserProfessionalEducationViewSet, UserRegionViewSet,
                         UsersParentViewSet, UserStatementDocumentsViewSet,
                         apply_for_verification)

app_name = 'api'

router = DefaultRouter()

router.register(r'save_users', SafeUserViewSet, basename='save_users')
router.register(r'rsousers', RSOUserViewSet, basename='rsousers')
router.register(r'regions', RegionViewSet)
router.register(r'areas', AreaViewSet)
router.register(r'districts', DistrictViewSet, basename='districts')
router.register(r'regionals', RegionalViewSet, basename='regionals')
router.register(r'educationals', EducationalViewSet)
router.register(r'locals', LocalViewSet)
router.register(r'detachments', DetachmentViewSet)
router.register(r'centrals', CentralViewSet, basename='centrals')
router.register(r'positions', PositionViewSet)
router.register(
    'eduicational_institutions',
    EducationalInstitutionViewSet,
    basename='educational-institution'
)
router.register('membership_certificates', MemberCertViewSet)
router.register('events', EventViewSet, basename='events')
router.register(
    r'events/(?P<event_pk>\d+)/group_applications/all',
    GroupEventApplicationViewSet,
    basename='group-applications'
)
router.register(
    r'events/(?P<event_pk>\d+)/applications',
    EventApplicationsViewSet,
    basename='event-applications'
)
router.register(
    r'events/(?P<event_pk>\d+)/participants',
    EventParticipantsViewSet,
    basename='event-participants'
)
router.register(
    r'events/(?P<event_pk>\d+)/answers',
    AnswerDetailViewSet,
    basename='answer'
)
router.register(
    r'events/(?P<event_pk>\d+)/user_documents',
    EventUserDocumentViewSet,
    basename='event-user-document'
)
router.register(
    r'events/(?P<event_pk>\d+)/multi_applications',
    MultiEventViewSet,
    basename='multi-applications'
)
router.register(
    r'competitions',
    CompetitionViewSet,
    basename='competition'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/applications',
    CompetitionApplicationsViewSet,
    basename='competition-applications'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/participants',
    CompetitionParticipantsViewSet,
    basename='competition-participants'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q2',
    Q2DetachmentReportViewSet,
    basename='q2'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q5',
    Q5DetachmentReportViewSet,
    basename='q5'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q7',
    Q7ViewSet,
    basename='q7'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q7/(?P<report_pk>\d+)/objects',
    Q7UpdateDestroyViewSet,
    basename='q7_update_destroy'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q8',
    Q8ViewSet,
    basename='q8'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q8/(?P<report_pk>\d+)/objects',
    Q8UpdateDestroyViewSet,
    basename='q8_update_destroy'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q9',
    Q9ViewSet,
    basename='q9'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q9/(?P<report_pk>\d+)/objects',
    Q9UpdateDestroyViewSet,
    basename='q9_update_destroy'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q10',
    Q10ViewSet,
    basename='q10'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q10/(?P<report_pk>\d+)/objects',
    Q10UpdateDestroyViewSet,
    basename='q10_update_destroy'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q11',
    Q11ViewSet,
    basename='q11'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q11/(?P<report_pk>\d+)/objects',
    Q11UpdateDestroyViewSet,
    basename='q11_update_destroy'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q12',
    Q12ViewSet,
    basename='q12'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q12/(?P<report_pk>\d+)/objects',
    Q12UpdateDestroyViewSet,
    basename='q12_update_destroy'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q14',
    Q14DetachmentReportViewSet,
    basename='q14_report'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q17',
    Q17DetachmentReportViewSet,
    basename='q17_report'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q19',
    Q19DetachmentReportViewset,
    basename='q19'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q20',
    Q20ViewSet,
    basename='q20'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q16',
    Q16ViewSet,
    basename='q16'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q18',
    Q18DetachmentReportViewSet,
    basename='q18'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q13',
    Q13DetachmentReportViewSet,
    basename='q13'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q13/(?P<report_pk>\d+)/objects',
    Q13EventOrganizationViewSet,
    basename='q13eventorganization'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q5/(?P<report_pk>\d+)/objects',
    Q5EducatedParticipantViewSet,
    basename='q5educatedparticipant'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q14/(?P<report_pk>\d+)/objects',
    Q14LaborProjectViewSet,
    basename='q14laborproject'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q17/(?P<report_pk>\d+)/objects',
    Q17EventLinkViewSet,
    basename='q17eventlink'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q15',
    Q15DetachmentReportViewSet,
    basename='q15'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q15/(?P<report_pk>\d+)/objects',
    Q15GrantDataViewSet,
    basename='q15grants'
)
router.register(
    r'competitions/(?P<competition_pk>\d+)/reports/q6',
    Q6DetachmentReportViewSet,
    basename='q6'
)

UserEduVS = UserEducationViewSet.as_view(UPDATE_RETRIEVE)
UserProfEduRetrieveCreateVS = UserProfessionalEducationViewSet.as_view(
    RETRIEVE_CREATE
)
UserProfEduPUDVS = UserProfessionalEducationViewSet.as_view(
    UPDATE_RETRIEVE | DELETE
)
UserDocVS = UserDocumentsViewSet.as_view(UPDATE_RETRIEVE)
UserRegVS = UserRegionViewSet.as_view(UPDATE_RETRIEVE)
UsersRegionsVS = UserRegionViewSet.as_view(LIST)
UserPrivacyVS = UserPrivacySettingsViewSet.as_view(UPDATE_RETRIEVE)
UserMediaVS = UserMediaViewSet.as_view(UPDATE_RETRIEVE)
UserStatementVS = UserStatementDocumentsViewSet.as_view(
    UPDATE_RETRIEVE
)
UsersParentVS = UsersParentViewSet.as_view(UPDATE_RETRIEVE)
DetachmentPositionVS = DetachmentPositionViewSet.as_view(CREATE_METHOD)
UserStatementMembershipDownloadVS = UserStatementDocumentsViewSet.as_view(
    DOWNLOAD_MEMBERSHIP_FILE
)
UserStatementConsentPDDownloadVS = UserStatementDocumentsViewSet.as_view(
    DOWNLOAD_CONSENT_PD
)
UserStatementParentConsentPDDownloadVS = UserStatementDocumentsViewSet.as_view(
    DOWNLOAD_PARENT_CONSENT_PD
)
UserStatementDownloadAllVS = UserStatementDocumentsViewSet.as_view(
    DOWNLOAD_ALL_FORMS
)
ForeignUserDocsVS = ForeignUserDocumentsViewSet.as_view(
    UPDATE_RETRIEVE
)
ForeignUserDocsListVS = ForeignUserDocumentsViewSet.as_view(LIST)
ForeignParentDocsVS = UserForeignParentDocsViewSet.as_view(
    RETRIEVE_CREATE | DELETE
)
ForeignParentDocsListVS = UserForeignParentDocsViewSet.as_view(LIST)
AdditionalDocsVS = AdditionalForeignDocsViewSet.as_view(
    DELETE
)
DetachmentAcceptVS = DetachmentAcceptViewSet.as_view(CREATE_DELETE)
DetachmentApplicationVS = DetachmentApplicationViewSet.as_view(CREATE_DELETE)
DetachmentPositionListVS = DetachmentPositionViewSet.as_view(LIST)
DetachmentPositionUpdateDeleteVS = DetachmentPositionViewSet.as_view(
    DELETE_UPDATE_RETRIEVE
)
# EducationalAcceptVS = EducationalAcceptViewSet.as_view(CREATE_DELETE)
# EducationalApplicationVS = EducationalApplicationViewSet.as_view(CREATE_DELETE)
EducationalPositionListVS = EducationalPositionViewSet.as_view(LIST)
EducationalPositionUpdateVS = EducationalPositionViewSet.as_view(
    UPDATE_RETRIEVE
)
# LocalAcceptVS = LocalAcceptViewSet.as_view(CREATE_DELETE)
# LocalApplicationVS = LocalApplicationViewSet.as_view(CREATE_DELETE)
LocalPositionListVS = LocalPositionViewSet.as_view(LIST)
LocalPositionUpdateVS = LocalPositionViewSet.as_view(UPDATE_RETRIEVE)
# RegionalAcceptVS = RegionalAcceptViewSet.as_view(CREATE_DELETE)
# RegionalApplicationVS = RegionalApplicationViewSet.as_view(CREATE_DELETE)
RegionalPositionListVS = RegionalPositionViewSet.as_view(LIST)
RegionalPositionUpdateVS = RegionalPositionViewSet.as_view(UPDATE_RETRIEVE)
# DistrictAcceptVS = DistrictAcceptViewSet.as_view(CREATE_DELETE)
# DistrictApplicationVS = DistrictApplicationViewSet.as_view(CREATE_DELETE)
DistrictPositionListVS = DistrictPositionViewSet.as_view(LIST)
DistrictPositionUpdateVS = DistrictPositionViewSet.as_view(UPDATE_RETRIEVE)
# CentralAcceptVS = CentralAcceptViewSet.as_view(CREATE_DELETE)
# CentralApplicationVS = CentralApplicationViewSet.as_view(CREATE_DELETE)
CentralPositionListVS = CentralPositionViewSet.as_view(LIST)
CentralPositionUpdateVS = CentralPositionViewSet.as_view(UPDATE_RETRIEVE)
EventOrganizationDataListVS = EventOrganizationDataViewSet.as_view(LIST_CREATE)
EventOrganizationDataObjVS = EventOrganizationDataViewSet.as_view(
    UPDATE_DELETE
)
EventAdditionalIssueListVS = EventAdditionalIssueViewSet.as_view(LIST_CREATE)
EventAdditionalIssueObjVS = EventAdditionalIssueViewSet.as_view(UPDATE_DELETE)
ExchangeTokenVS = ExchangeTokenView.as_view(EXCHANGE_TOKEN)

user_nested_urls = [
    path('regions/users_list', UsersRegionsVS, name='user-regions'),
    path('rsousers/me/education/', UserEduVS, name='user-education'),
    path('rsousers/me/documents/', UserDocVS, name='user-documents'),
    path(
        'rsousers/me/foreign_documents/',
        ForeignUserDocsVS,
        name='foreign-documents'
    ),
    path(
        'rsousers/foreign_documents/<int:pk>/',
        ForeignUserDocsListVS,
        name='foreign-documents-list'
    ),
    path(
        'rsousers/me/foreign_parent_documents/',
        ForeignParentDocsVS,
        name='foreign-parent-documents'
    ),
    path(
        'rsousers/foreign_parent_documents/<int:pk>/',
        ForeignParentDocsListVS,
        name='foreign-parent-documents-list'
    ),
    path(
        'rsousers/me/foreign_parent_additional_documents/<int:pk>/',
        AdditionalDocsVS,
        name='foreign-parent-additional-documents'
    ),
    path('rsousers/me/region/', UserRegVS, name='user-region'),
    path('rsousers/me/privacy/', UserPrivacyVS, name='user-privacy'),
    path('rsousers/me/media/', UserMediaVS, name='user-media'),
    path('rsousers/me/statement/', UserStatementVS, name='user-statement'),
    path('rsousers/me/parent/', UsersParentVS, name='user-parent'),
    path(
        'rsousers/me/statement/download_membership_statement_file/',
        UserStatementMembershipDownloadVS,
        name='download-membership-file'
    ),
    path(
        (
            'rsousers/me/statement/'
            'download_consent_to_the_processing_of_personal_data/'
        ),
        UserStatementConsentPDDownloadVS,
        name='download-consent-pd'
    ),
    path(
        (
            'rsousers/me/statement/'
            'download_parent_consent_to_the_processing_of_personal_data/'
        ),
        UserStatementParentConsentPDDownloadVS,
        name='download-parent-consent-pd'
    ),
    path(
        'rsousers/me/statement/download_all_forms/',
        UserStatementDownloadAllVS,
        name='download-all-forms'
    ),
    path(
        'rsousers/me/apply_for_verification/',
        apply_for_verification,
        name='user-verification'
    ),
    path(
        'rsousers/<int:pk>/verify/',
        verify_user,
        name='user-verify'
    ),
    path(
        'rsousers/<int:pk>/membership_fee_status/',
        change_membership_fee_status,
        name='user-membership-fee'
    ),
    path(
        'detachments/<int:pk>/apply/',
        DetachmentApplicationVS,
        name='detachment-application'
    ),
    path(
        'detachments/<int:pk>/applications/<int:application_pk>/accept/',
        DetachmentAcceptVS,
        name='user-apply'
    ),
    path(
        'detachments/<int:pk>/members/',
        DetachmentPositionListVS,
        name='detachment-members-list'
    ),
    path(
        'detachments/<int:pk>/members/<int:membership_pk>/',
        DetachmentPositionUpdateDeleteVS,
        name='detachment-members-update'
    ),
    path(
        'detachments/<int:detachment_pk>/competitions/<int:competition_pk>/place/',
        get_detachment_place,
        name='detachment-competition-place'
    ),
    path(
        'detachments/<int:detachment_pk>/competitions/<int:competition_pk>/is_tandem/',
        DetachmentCompetitionIsTandemView.as_view(),
        name='detachment-competition-place'
    ),
    # path(
    #     'educationals/<int:pk>/apply/',
    #     EducationalApplicationVS,
    #     name='educational-application'
    # ),
    # path(
    #     'educationals/<int:pk>/applications/<int:application_pk>/accept/',
    #     EducationalAcceptVS,
    #     name='user-edu-apply'
    # ),
    path(
        'educationals/<int:pk>/members/',
        EducationalPositionListVS,
        name='educational-members-list'
    ),
    path(
        'educationals/<int:pk>/members/<int:membership_pk>/',
        EducationalPositionUpdateVS,
        name='educational-members-update'
    ),
    path(
        'locals/<int:pk>/members/',
        LocalPositionListVS,
        name='local-members-list'
    ),
    path(
        'locals/<int:pk>/members/<int:membership_pk>/',
        LocalPositionUpdateVS,
        name='local-members-update'
    ),
    # path(
    #     'locals/<int:pk>/apply/',
    #     LocalApplicationVS,
    #     name='local-application'
    # ),
    # path(
    #     'locals/<int:pk>/applications/<int:application_pk>/accept/',
    #     LocalAcceptVS,
    #     name='user-local-apply'
    # ),
    path(
        'regionals/<int:pk>/members/',
        RegionalPositionListVS,
        name='regional-members-list'
    ),
    path(
        'regionals/<int:pk>/members/<int:membership_pk>/',
        RegionalPositionUpdateVS,
        name='regional-members-update'
    ),
    # path(
    #     'regionals/<int:pk>/apply/',
    #     RegionalApplicationVS,
    #     name='regional-application'
    # ),
    # path(
    #     'regionals/<int:pk>/applications/<int:application_pk>/accept/',
    #     RegionalAcceptVS,
    #     name='user-regional-apply'
    # ),
    path(
        'districts/<int:pk>/members/',
        DistrictPositionListVS,
        name='district-members-list'
    ),
    path(
        'districts/<int:pk>/members/<int:membership_pk>/',
        DistrictPositionUpdateVS,
        name='district-members-update'
    ),
    # path(
    #     'districts/<int:pk>/apply/',
    #     DistrictApplicationVS,
    #     name='district-application'
    # ),
    # path(
    #     'districts/<int:pk>/applications/<int:application_pk>/accept/',
    #     DistrictAcceptVS,
    #     name='user-district-apply'
    # ),
    path(
        'centrals/<int:pk>/members/',
        CentralPositionListVS,
        name='central-members-list'
    ),
    path(
        'centrals/<int:pk>/members/<int:membership_pk>/',
        CentralPositionUpdateVS,
        name='central-members-update'
    ),
    # path(
    #     'centrals/<int:pk>/apply/',
    #     CentralApplicationVS,
    #     name='central-application'
    # ),
    # path(
    #     'centrals/<int:pk>/applications/<int:application_pk>/accept/',
    #     CentralAcceptVS,
    #     name='user-central-apply'
    # ),
    path(
        'rsousers/me/professional_education/',
        UserProfEduRetrieveCreateVS,
        name='user-prof-education_retrieve_create',
    ),
    path(
        'rsousers/me/professional_education/<int:pk>/',
        UserProfEduPUDVS,
        name='user-prof-education_post_update_delete',
    ),
    path(
        'structural_units/',
        get_structural_units,
        name='structural-units'
    ),
    path(
        'events/<int:event_pk>/organizers/',
        EventOrganizationDataListVS,
        name='event-organization-list'
    ),
    path(
        'events/<int:event_pk>/organizers/<int:pk>/',
        EventOrganizationDataObjVS,
        name='event-organization-objects'
    ),
    path(
        'events/<int:event_pk>/issues/',
        EventAdditionalIssueListVS,
        name='event-organization-list'
    ),
    path(
        'events/<int:event_pk>/issues/<int:pk>/',
        EventAdditionalIssueObjVS,
        name='event-organization-objects'
    ),
    path(
        'events/<int:event_pk>/answers/',
        create_answers,
        name='create-answers'
    ),
    path(
        'events/<int:event_pk>/group_applications/',
        group_applications,
        name='get-group-applications'
    ),
    path(
        'events/<int:event_pk>/group_applications/me/',
        group_applications_me,
        name='get-group-applications-me'
    ),
    path(
        'events/<int:event_pk>/user_status/<int:user_pk>/',
        is_participant_or_applicant,
        name='is-participant-or-applicant'
    ),
    path(
        'competitions/<int:competition_pk>/reports/q1/get-place/',
        get_place_q1,
        name='get-place-q1'
    ),
    path(
        'competitions/<int:competition_pk>/reports/q1/info/',
        get_q1_info,
        name='get-q1-info'
    ),
    path(
        'competitions/<int:competition_pk>/reports/q3/get-place/',
        get_place_q3,
        name='get-place-q3'
    ),
    path(
        'competitions/<int:competition_pk>/reports/q4/get-place/',
        get_place_q4,
        name='get-place-q4'
    ),
    path(
        'competitions/<int:competition_pk>/verification_logs/<int:q_number>/',
        QVerificationLogByNumberView.as_view(),
        name='get-verification-log',
    ),
    path(
        'competitions/<int:competition_pk>/get-place/',
        get_place_overall,
        name='get-place-overall'
    ),
    path(
        'competitions/<int:competition_pk>/get-detachment-places/<int:detachment_pk>/',
        get_detachment_places,
        name='get-detachment-places'
    ),
    path('', include('djoser.urls')),
    path('exchange-token/', ExchangeTokenVS, name='exchange-token'),
]

urlpatterns = [
    path('register/', UserViewSet.as_view(CREATE_METHOD), name='user-create'),
    path(
        'reset_password/',
        CustomUserViewSet.as_view(POST_RESET_PASSWORD),
        name='reset_password'
    ),
    path(
        'rsousers', CustomUserViewSet.as_view(LIST),
    ),
    path('questions/', QuestionsView.as_view(), name='questions'),
    path('submit_answers/', submit_answers, name='submit-answers'),
    path('get_attempts_status/', get_attempts_status, name='get-attempts-status'),
    path('jwt/vk-login/', VKLoginAPIView.as_view(), name='vk_login'),
    path('', include(router.urls)),
] + user_nested_urls
