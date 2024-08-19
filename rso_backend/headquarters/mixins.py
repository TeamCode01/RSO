from typing import Callable

from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from headquarters.swagger_schemas import applications_response
from headquarters.models import (UserDetachmentApplication, CentralHeadquarter, DistrictHeadquarter,           RegionalHeadquarter, LocalHeadquarter, EducationalHeadquarter, Detachment, 
    UserCentralHeadquarterPosition, UserDistrictHeadquarterPosition, 
    UserRegionalHeadquarterPosition, UserLocalHeadquarterPosition, 
    UserEducationalHeadquarterPosition, UserDetachmentPosition)
from headquarters.serializers import (CentralPositionSerializer, DistrictPositionSerializer, 
    RegionalPositionSerializer, LocalPositionSerializer, 
    EducationalPositionSerializer, DetachmentPositionSerializer)
from django.db.models import Q
from django.db.models.query import QuerySet
from django.conf import settings


class ApplicationsMixin:
    def get_application_model(self):
        raise NotImplementedError("Необходимо определить метод get_application_model")

    def get_application_serializer(self):
        raise NotImplementedError("Необходимо определить метод get_application_serializer")

    def get_application_short_serializer(self):
        raise NotImplementedError("Необходимо определить метод get_application_short_serializer")

    @action(detail=True, methods=['get'], url_path='applications')
    @swagger_auto_schema(responses=applications_response)
    def get_applications(self, request, pk=None):
        """Получить список заявок на вступление в штаб."""
        headquarter = self.get_object()
        user_id = request.query_params.get('user_id')
        application_model = self.get_application_model()
        if application_model is UserDetachmentApplication:
            applications = application_model.objects.filter(
                detachment=headquarter
            )
        else:
            applications = application_model.objects.filter(
                headquarter=headquarter
            )
        if user_id:
            applications = applications.filter(user_id=user_id)
        serializer = self.get_application_serializer()(instance=applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='applications_short')
    @swagger_auto_schema(responses=applications_response)
    def get_applications_short(self, request, pk=None):
        """Получить список заявок на вступление в штаб c мин. инф о юзере."""
        headquarter = self.get_object()
        user_id = request.query_params.get('user_id')
        application_model = self.get_application_model()
        if application_model is UserDetachmentApplication:
            applications = application_model.objects.filter(
                detachment=headquarter
            )
        else:
            applications = application_model.objects.filter(
                headquarter=headquarter
            )
        if user_id:
            applications = applications.filter(user_id=user_id)
        serializer = self.get_application_short_serializer()(instance=applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VerificationsMixin:
    def get_func_members_to_verify(self) -> Callable:
        raise NotImplementedError("Необходимо определить метод get_members_to_verify")

    def get_verification_model(self):
        raise NotImplementedError("Необходимо определить метод get_verification_model")

    def get_verification_serializer(self):
        raise NotImplementedError("Необходимо определить метод get_verification_serializer")

    @action(detail=True, methods=['get'], url_path='verifications')
    def get_verifications(self, request, pk=None):
        """
        Получить список пользователей, подавших заявку на верификацию,
        у которых совпадает регион с регионом текущего штаба.
        """
        headquarter = self.get_object()
        user_id = request.query_params.get('user_id')
        members_to_verify = self.get_func_members_to_verify()(headquarter)
        if user_id:
            members_to_verify = members_to_verify.filter(user_id=user_id)
        serializer = self.get_verification_serializer()(instance=members_to_verify, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubControlBaseMixin:
    def get_sub_controls(self, headquarters):
        sub_control = []
        for hq in headquarters:
            sub_control.append({
                'id': hq.id,
                'name': hq.name,
            })
        return sub_control
    

class SubDistrictHqsMixin(SubControlBaseMixin):
    
    @action(detail=True, methods=['get'], url_path='sub_regionals')
    def get_sub_regionals(self, request, pk=None):
        district_hq = self.get_object()
        regionals = RegionalHeadquarter.objects.filter(district_headquarter=district_hq)
        sub_control_data = self.get_sub_controls(regionals)
        return Response(sub_control_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='sub_locals')
    def get_sub_locals(self, request, pk=None):
        district_hq = self.get_object()
        locals = LocalHeadquarter.objects.filter(regional_headquarter__district_headquarter=district_hq)
        sub_control_data = self.get_sub_controls(locals)
        return Response(sub_control_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='sub_educationals')
    def get_sub_educationals(self, request, pk=None):
        district_hq = self.get_object()
        educationals = EducationalHeadquarter.objects.filter(regional_headquarter__district_headquarter=district_hq)
        sub_control_data = self.get_sub_controls(educationals)
        return Response(sub_control_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='sub_detachments')
    def get_sub_detachments(self, request, pk=None):
        district_hq = self.get_object()
        detachments = Detachment.objects.filter(regional_headquarter__district_headquarter=district_hq)
        sub_control_data = self.get_sub_controls(detachments)
        return Response(sub_control_data, status=status.HTTP_200_OK)


class SubRegionalHqsMixin(SubControlBaseMixin):
    
    @action(detail=True, methods=['get'], url_path='sub_locals')
    def get_sub_locals(self, request, pk=None):
        regional_hq = self.get_object()
        locals = LocalHeadquarter.objects.filter(regional_headquarter=regional_hq)
        sub_control_data = self.get_sub_controls(locals)
        return Response(sub_control_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='sub_educationals')
    def get_sub_educationals(self, request, pk=None):
        regional_hq = self.get_object()
        educationals = EducationalHeadquarter.objects.filter(regional_headquarter=regional_hq)
        sub_control_data = self.get_sub_controls(educationals)
        return Response(sub_control_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='sub_detachments')
    def get_sub_detachments(self, request, pk=None):
        regional_hq = self.get_object()
        detachments = Detachment.objects.filter(regional_headquarter=regional_hq)
        sub_control_data = self.get_sub_controls(detachments)
        return Response(sub_control_data, status=status.HTTP_200_OK)


class SubLocalHqsMixin(SubControlBaseMixin):
    
    @action(detail=True, methods=['get'], url_path='sub_educationals')
    def get_sub_educationals(self, request, pk=None):
        local_hq = self.get_object()
        educationals = EducationalHeadquarter.objects.filter(local_headquarter=local_hq)
        sub_control_data = self.get_sub_controls(educationals)
        return Response(sub_control_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='sub_detachments')
    def get_sub_detachments(self, request, pk=None):
        local_hq = self.get_object()
        detachments = Detachment.objects.filter(local_headquarter=local_hq)
        sub_control_data = self.get_sub_controls(detachments)
        return Response(sub_control_data, status=status.HTTP_200_OK)


class SubEducationalHqsMixin(SubControlBaseMixin):
    
    @action(detail=True, methods=['get'], url_path='sub_detachments')
    def get_sub_detachments(self, request, pk=None):
        educational_hq = self.get_object()
        detachments = Detachment.objects.filter(educational_headquarter=educational_hq)
        sub_control_data = self.get_sub_controls(detachments)
        return Response(sub_control_data, status=status.HTTP_200_OK)
    

class BaseLeadershipMixin:
    _POSITIONS_MAPPING = {
        CentralHeadquarter: (
            UserCentralHeadquarterPosition, CentralPositionSerializer
        ),
        DistrictHeadquarter: (
            UserDistrictHeadquarterPosition, DistrictPositionSerializer
        ),
        RegionalHeadquarter: (
            UserRegionalHeadquarterPosition, RegionalPositionSerializer
        ),
        LocalHeadquarter: (
            UserLocalHeadquarterPosition, LocalPositionSerializer
        ),
        EducationalHeadquarter: (
            UserEducationalHeadquarterPosition, EducationalPositionSerializer
        ),
        Detachment: (UserDetachmentPosition, DetachmentPositionSerializer),
    }

    def _get_position_instance(self, instance):
        instance_type = type(instance)
        for model_class, (position_model, _) in self._POSITIONS_MAPPING.items():
            if issubclass(instance_type, model_class):
                return position_model

    def _get_position_serializer(self, instance):
        instance_type = type(instance)
        for model_class, (_, serializer_class) in self._POSITIONS_MAPPING.items():
            if issubclass(instance_type, model_class):
                return serializer_class

    def get_leadership(self, instance):
        """
        Получает список руководства для данного штаба, исключая должности, указанные в настройках.
        """
        position_model = self._get_position_instance(instance)
        serializer_class = self._get_position_serializer(instance)
        
        leaders = position_model.objects.filter(
            headquarter=instance
        ).exclude(
            Q(position__name__in=settings.NOT_LEADERSHIP_POSITIONS) |
            Q(position__isnull=True)
        )
        return serializer_class(leaders, many=True).data

    @action(detail=True, methods=['get'], url_path='leadership')
    def leadership_action(self, request, pk=None):
        instance = self.get_object()
        leadership_data = self.get_leadership(instance)
        return Response(leadership_data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], url_path='leadership/(?P<user_pk>\d+)')
    def retrieve_leadership_by_user_pk(self, request, pk=None, user_pk=None):
        instance = self.get_object()
        leadership_data = self.get_leadership(instance)
        filtered_leadership = [leader for leader in leadership_data if leader['user']['id'] == int(user_pk)]
        if filtered_leadership:
            return Response(filtered_leadership, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


class DetachmentLeadershipMixin(BaseLeadershipMixin):
    class Meta:
         model = Detachment
         fields = ('leadership',)

    def get_leadership(self, instance):
        """
        Получает список руководства отряда (только "Мастер (методист)" и "Комиссар").
        """
        position_model = self._get_position_instance(instance)
        serializer_class = self._get_position_serializer(instance)
        
        leaders = position_model.objects.filter(
            Q(headquarter=instance) &
            (
                Q(position__name=settings.MASTER_METHODIST_POSITION_NAME) |
                Q(position__name=settings.COMMISSIONER_POSITION_NAME)
            )
        )
        return serializer_class(leaders, many=True).data
    

class BaseSubCommanderMixin:
    def add_commanders(self, headquarters, user_id, commanders, hq_type):
        for hq in headquarters:
            if hq.commander and (user_id is None or hq.commander.id == int(user_id)):
                commanders.append({
                    'id': hq.commander.id,
                    'type': hq_type,
                    'commander': hq.commander.get_full_name() if hasattr(hq.commander, 'get_full_name') else str(hq.commander),
                    'unit': hq.name
                })
        return commanders

    def append_district_hqs(self, district_headquarters, user_id, commanders):
        return self.add_commanders(district_headquarters, user_id, commanders, 'DistrictHeadquarter')

    def append_regional_hqs(self, regional_headquarters, user_id, commanders):
        return self.add_commanders(regional_headquarters, user_id, commanders, 'RegionalHeadquarter')

    def append_detachment_hqs(self, detachments, user_id, commanders):
        return self.add_commanders(detachments, user_id, commanders, 'Detachment')

    def append_local_hqs(self, local_headquarters, user_id, commanders):
        return self.add_commanders(local_headquarters, user_id, commanders, 'LocalHeadquarter')

    def append_educational_hqs(self, educational_headquarters, user_id, commanders):
        return self.add_commanders(educational_headquarters, user_id, commanders, 'EducationalHeadquarter')

    @action(detail=True, methods=['get'], url_path='sub_commanders')
    def retrieve_sub_commanders(self, request, pk=None):
        instance = self.get_object()
        commanders = self.get_sub_commanders(instance)
        return Response(commanders, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='sub_commanders/(?P<user_pk>\d+)')
    def retrieve_sub_commander_by_user_pk(self, request, pk=None, user_pk=None):
        instance = self.get_object()
        commanders = self.get_sub_commanders(instance)
        filtered_commanders = [cmd for cmd in commanders if cmd['id'] == int(user_pk)]
        if filtered_commanders:
            return Response(filtered_commanders, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


class CentralSubCommanderMixin(BaseSubCommanderMixin):
    def get_sub_commanders(self, obj):
        user_id = self.request.query_params.get('user_id', None)
        commanders = []
        central_headquarter = obj

        district_headquarters = DistrictHeadquarter.objects.filter(central_headquarter=central_headquarter)
        self.append_district_hqs(district_headquarters, user_id, commanders)

        regional_headquarters = RegionalHeadquarter.objects.filter(district_headquarter__central_headquarter=central_headquarter)
        self.append_regional_hqs(regional_headquarters, user_id, commanders)

        detachments = Detachment.objects.filter(regional_headquarter__district_headquarter__central_headquarter=central_headquarter)
        self.append_detachment_hqs(detachments, user_id, commanders)

        local_headquarters = LocalHeadquarter.objects.filter(regional_headquarter__district_headquarter__central_headquarter=central_headquarter)
        self.append_local_hqs(local_headquarters, user_id, commanders)

        educational_headquarters = EducationalHeadquarter.objects.filter(regional_headquarter__district_headquarter__central_headquarter=central_headquarter)
        self.append_educational_hqs(educational_headquarters, user_id, commanders)

        return commanders


class DistrictSubCommanderMixin(BaseSubCommanderMixin):
    def get_sub_commanders(self, obj):
        user_id = self.request.query_params.get('user_id', None)
        commanders = []
        district_headquarter = obj

        regional_headquarters = RegionalHeadquarter.objects.filter(district_headquarter=district_headquarter)
        self.append_regional_hqs(regional_headquarters, user_id, commanders)

        detachments = Detachment.objects.filter(regional_headquarter__district_headquarter=district_headquarter)
        self.append_detachment_hqs(detachments, user_id, commanders)

        local_headquarters = LocalHeadquarter.objects.filter(regional_headquarter__district_headquarter=district_headquarter)
        self.append_local_hqs(local_headquarters, user_id, commanders)

        educational_headquarters = EducationalHeadquarter.objects.filter(regional_headquarter__district_headquarter=district_headquarter)
        self.append_educational_hqs(educational_headquarters, user_id, commanders)

        return commanders


class RegionalSubCommanderMixin(BaseSubCommanderMixin):
    def get_sub_commanders(self, obj):
        user_id = self.request.query_params.get('user_id', None)
        commanders = []
        regional_headquarter = obj

        detachments = Detachment.objects.filter(regional_headquarter=regional_headquarter)
        self.append_detachment_hqs(detachments, user_id, commanders)

        local_headquarters = LocalHeadquarter.objects.filter(regional_headquarter=regional_headquarter)
        self.append_local_hqs(local_headquarters, user_id, commanders)

        educational_headquarters = EducationalHeadquarter.objects.filter(regional_headquarter=regional_headquarter)
        self.append_educational_hqs(educational_headquarters, user_id, commanders)

        return commanders


class LocalSubCommanderMixin(BaseSubCommanderMixin):
    def get_sub_commanders(self, obj):
        user_id = self.request.query_params.get('user_id', None)
        commanders = []
        local_headquarter = obj

        detachments = Detachment.objects.filter(local_headquarter=local_headquarter)
        self.append_detachment_hqs(detachments, user_id, commanders)

        educational_headquarters = EducationalHeadquarter.objects.filter(local_headquarter=local_headquarter)
        self.append_educational_hqs(educational_headquarters, user_id, commanders)

        return commanders


class EducationalSubCommanderMixin(BaseSubCommanderMixin):
    def get_sub_commanders(self, obj):
        user_id = self.request.query_params.get('user_id', None)
        commanders = []
        educational_headquarter = obj

        detachments = Detachment.objects.filter(educational_headquarter=educational_headquarter)
        self.append_detachment_hqs(detachments, user_id, commanders)
        
        return commanders