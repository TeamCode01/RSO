from typing import Callable

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from headquarters.swagger_schemas import applications_response
from headquarters.models import UserDetachmentApplication


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


class SubControlHeadquartersMixin: 
    def get_sub_control_serializer(self):
        raise NotImplementedError("Необходимо определить метод get_headquarter_serializer")
    
    @action(detail=True, methods=['get'], url_path='sub_regionals')
    def districts_sub_regionals_headquarters(self, request, pk=None):
        district = self.get_object()
        serializer = self.get_serializer(district, context={'type': 'regional'})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='sub_locals')
    def districts_sub_locals_headquarters(self, request, pk=None):
        district = self.get_object()
        serializer = self.get_serializer(district, context={'type': 'local'})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='sub_educationals')
    def districts_sub_educationals_headquarters(self, request, pk=None):
        district = self.get_object()
        serializer = self.get_serializer(district, context={'type': 'educational'})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='sub_locals')
    def regional_sub_locals_headquarters(self, request, pk=None):
        regional = self.get_object()
        serializer = self.get_serializer(regional, context={'type': 'local'})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='sub_educationals')
    def regional_sub_educationals_headquarters(self, request, pk=None):
        regional = self.get_object()
        serializer = self.get_serializer(regional, context={'type': 'educational'})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='sub_educationals')
    def local_sub_educationals_headquarters(self, request, pk=None):
        local = self.get_object()
        serializer = self.get_serializer(local, context={'type': 'educational'})
        return Response(serializer.data)
    
    