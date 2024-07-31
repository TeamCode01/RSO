from django.utils.decorators import method_decorator
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from headquarters.swagger_schemas import applications_response


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
        applications = self.get_application_model().objects.filter(
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
        applications = self.get_application_model().objects.filter(
            headquarter=headquarter
        )
        if user_id:
            applications = applications.filter(user_id=user_id)
        serializer = self.get_application_short_serializer()(instance=applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VerificationsMixin:
    def get_func_members_to_verify(self):
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
        members_to_verify = self.get_members_to_verify()(headquarter)
        if user_id:
            members_to_verify = members_to_verify.filter(user_id=user_id)
        serializer = self.get_verification_serializer()(instance=members_to_verify, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
