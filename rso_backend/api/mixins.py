from contextlib import suppress
import datetime
import json

import django.core.exceptions
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils.timezone import now
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response


class RetrieveViewSet(mixins.RetrieveModelMixin,
                      GenericViewSet):
    """Миксин, разрешающий методы чтения только у конкретного юзера."""
    pass


class RetrieveUpdateViewSet(mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            GenericViewSet):
    """Миксин, разрешающий методы чтения только у конкретного юзера."""
    pass


class ListRetrieveViewSet(mixins.RetrieveModelMixin,
                          mixins.ListModelMixin,
                          GenericViewSet):
    """Миксин, разрешающий только методы чтения."""
    pass


class ListRetrieveUpdateViewSet(mixins.RetrieveModelMixin,
                                mixins.ListModelMixin,
                                mixins.UpdateModelMixin,
                                GenericViewSet):
    """
    Миксин для эндпоинта /user, разрешающий только методы чтения и обновления.
    """
    pass


class CreateViewSet(mixins.CreateModelMixin,
                    GenericViewSet):
    pass


class CreateDeleteViewSet(mixins.CreateModelMixin,
                          mixins.DestroyModelMixin,
                          GenericViewSet):
    pass


class CreateListRetrieveDestroyViewSet(mixins.CreateModelMixin,
                                       mixins.ListModelMixin,
                                       mixins.RetrieveModelMixin,
                                       mixins.DestroyModelMixin,
                                       GenericViewSet):
    """
    Миксин для эндпоинта /events/<event_pk>/applications/
    разрешающий все методы, кроме обновления.
    """
    pass


class ListRetrieveDestroyViewSet(mixins.ListModelMixin,
                                 mixins.RetrieveModelMixin,
                                 mixins.DestroyModelMixin,
                                 GenericViewSet):
    """
    Миксин для эндпоинта /events/<event_pk>/participants/
    разрешающий только методы чтения и удаления.
    """
    pass


class RetrieveUpdateDestroyViewSet(mixins.RetrieveModelMixin,
                                   mixins.UpdateModelMixin,
                                   mixins.DestroyModelMixin,
                                   GenericViewSet):
    """
    Миксин для эндпоинта /events/<event_pk>/answers/
    разрешающий только методы чтения(retrieve) удаления и обновления.
    """
    pass


class CreateRetrieveUpdateViewSet(mixins.CreateModelMixin,
                                  mixins.RetrieveModelMixin,
                                  mixins.UpdateModelMixin,
                                  GenericViewSet):
    """
    Миксин для эндпоинта /events/<event_pk>/user_documents/
    разрешающий только все методы, кроме чтения (list) и удаления.
    """
    pass


class ListRetrieveCreateViewSet(mixins.RetrieveModelMixin,
                                mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                GenericViewSet):
    """Миксин для конкурсных показателей (отчеты)."""
    pass


class UpdateDestroyViewSet(mixins.UpdateModelMixin,
                           mixins.DestroyModelMixin,
                           GenericViewSet):
    """Миксин для вложенных объектов 13 конкурсного показателя."""
    pass


class CreateListRetrieveUpdateViewSet(mixins.CreateModelMixin,
                                      mixins.RetrieveModelMixin,
                                      mixins.UpdateModelMixin,
                                      mixins.ListModelMixin,
                                      GenericViewSet):
    pass


class SendMixin:

    @action(
        detail=True,
        methods=['POST'],
        url_path='send',
    )
    def send_for_verification(self, request, pk=None):
        """Отправляет отчет на верификацию.

        Метод идемпотентен. В случае успешной отправки возвращает `HTTP 200 OK`.
        """
        regional_r = self.get_object()
        # TODO: Перенести в один из последних показателей и раскомментировать
        # TODO: Заменить принты на логи
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=45,
            period=IntervalSchedule.SECONDS,
        )
        with suppress(django.core.exceptions.ValidationError):
            f, created = PeriodicTask.objects.get_or_create(
                interval=schedule,
                name=f'Send Email to reg hq id {regional_r.regional_headquarter.id}',
                task='regional_competitions.tasks.send_email_report_part_2',
                args=json.dumps([regional_r.regional_headquarter.id])
            )

            print(f'Получили таску: {f}. created: {created}. task expires: {f.expires}')

            if not f.expires or f.expires < now():
                print('Таска истекла или нет времени истечения. Устанавливаем актуальное время истечения...')
            elif created:
                f.expires = now() + datetime.timedelta(seconds=3600)
                f.save()
                print(f'Новая таска создана. Expiration time: {f.expires}')
            else:
                print(f'Таска уже существует и еще не истекла. Expiration time: {f.expires}')
        if hasattr(regional_r, 'is_sent'):
            regional_r.is_sent = True
            regional_r.save()
            return Response(
                {'detail': 'Данные отправлены на верификацию окружному штабу'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
