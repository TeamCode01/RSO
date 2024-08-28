import io
import mimetypes
import os
import re
import zipfile
import datetime
import time

from django.utils import timezone
from datetime import datetime

from django.db import IntegrityError
from django.db.models import Q
from django.http import QueryDict
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404

from requestlogs.base import SETTINGS
from requestlogs.logging import get_request_id
from requestlogs.utils import get_client_ip, remove_secrets

from regional_competitions.r_calculations import calculate_r5_score
from rest_framework.request import Request
from rest_framework import serializers, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from competitions.models import CompetitionParticipants
from headquarters.models import (CentralHeadquarter, Detachment,
                                 DistrictHeadquarter, RegionalHeadquarter,
                                 UserCentralHeadquarterPosition,
                                 UserDetachmentPosition,
                                 UserDistrictHeadquarterPosition,
                                 UserEducationalHeadquarterPosition,
                                 UserLocalHeadquarterPosition,
                                 UserRegionalHeadquarterPosition)
from users.models import RSOUser

from rest_framework.pagination import LimitOffsetPagination


class Limit250OffsetPagination(LimitOffsetPagination):
    default_limit = 100
    max_limit = 250

    def paginate_queryset(self, queryset, request, view=None):
        if request.user.is_authenticated and request.query_params.get('limit') == '-1':
            self.limit = len(queryset)
            self.offset = 0
            self.count = len(queryset)
            return list(queryset)
        return super().paginate_queryset(queryset, request, view)


class RegionOffsetPagination(Limit250OffsetPagination):
    def paginate_queryset(self, queryset, request, view=None):
        if request.query_params.get('limit') == '-1':
            self.limit = len(queryset)
            self.offset = 0
            self.count = len(queryset)
            return list(queryset)
        return super().paginate_queryset(queryset, request, view)



def create_first_or_exception(self, validated_data, instance, error_msg: str):
    """
    Создает запись или выводит исключение, если уже есть связанная
    с пользователем запись.
    """
    try:
        return instance.objects.create(**validated_data)
    except IntegrityError:
        raise serializers.ValidationError({'detail': error_msg})


def download_file(filepath, filename, reading_mode='r'):
    """Функция скачивания бланков заявлений.

    На вход получает путь до файла и имя файла.
    """

    if os.path.exists(filepath):
        path = open(filepath, reading_mode)
        mime_type, _ = mimetypes.guess_type(filepath)
        response = HttpResponse(path, content_type=mime_type)
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response
    else:
        return Response(
            {'detail': 'Файл не найден.'},
            status=status.HTTP_204_NO_CONTENT
        )


def is_safe_method(request):
    """Проверка методов пользователя при запросе к эндпоинту.

    Безопасные возвращают True.
    """

    return request.method in SAFE_METHODS


def is_stuff_or_central_commander(request):
    """Проверка роли пользователя.

    При запросе пользователя к эндпоинту проверяет роль пользователя.
    Если роль совпала с ролью админа или командира ЦШ, возвращает True.
    """

    check_central_commander = False
    try:
        commander_id = CentralHeadquarter.objects.get(
            commander_id=request.user.id
        ).commander_id
        if request.user.id == commander_id:
            check_central_commander = True
    except (CentralHeadquarter.DoesNotExist, AttributeError):
        check_central_commander = False
    return (request.user.is_authenticated
            and any([
                check_central_commander,
                request.user.is_superuser,
                request.user.is_staff
            ]))


def check_commander_or_not(request, headquarters):
    """Проверка является ли юзер командиром.

    headquarters - список моделей, в которых проверяется роль пользователя.
    request - запрос к эндпоинту
    """
    result = False
    for headquarter in headquarters:
        try:
            if headquarter.objects.get(
                    commander_id=request.user.id
            ) is not None:
                result = True
                break
        except (headquarter.DoesNotExist, AttributeError):
            pass
    return result


def check_role_get(request, model, position_in_quarter):
    """Проверка роли пользователя.

    model - модель 'Члены штаба'/'Члены отряда',
    в котором проверяется должность пользователя.
    request - запрос к эндпоинту
    position_in_quarter - требуемая должность для получения True.
    """

    try:
        user_headquarter_object = model.objects.get(user_id=request.user.id)
        position_name = (
            user_headquarter_object.position.name
            if user_headquarter_object.position else None
        )
    except (model.DoesNotExist, AttributeError):
        return False
    return (
            request.user.is_authenticated and position_name == position_in_quarter
    )


def search_trusted_in_list(user_id, tables_list):
    """Поиск первого доверенного пользователя в списке таблиц.

    tables_list - список таблиц, в котором производится поиск.
    """

    index = 0
    number_of_tables = len(tables_list)
    while index < number_of_tables:
        try:
            if tables_list[index].objects.get(
                    user_id=user_id
            ).is_trusted:
                return True
            index += 1
        except (tables_list[index].DoesNotExist, AttributeError):
            index += 1
    return False


def check_trusted_user(request, model, obj):
    """Проверка доверенного пользователя.

    model - модель штаба/отряда, в котором проверяется статус доверенности.
    request - запрос к эндпоинту.
    Функция проверяет является ли пользователь доверенным
    в той структурной единице, к которой пользователь сделал запрос.
    """

    try:
        member = model.objects.filter(
            user_id=request.user.id,
            headquarter_id=obj.id
        ).first()
        is_trusted = member.is_trusted
    except AttributeError:
        return False
    return (
            request.user.is_authenticated and is_trusted
    )


def check_trusted_for_detachments(request, obj=None):
    """Проверка доверенного пользователя для отряда.

    request - запрос к эндпоинту.
    obj - отряд, к которому пользователь сделал запрос.
    Управлять отрядом может любой доверенный пользователь из отряда
    или из штабов. Функция проверяет существует ли запись о юзере
    в штабах выше и если существует, то возвращает статус доверенности.
    """

    tables_for_check = [
        UserDetachmentPosition,
        UserEducationalHeadquarterPosition,
        UserLocalHeadquarterPosition,
        UserRegionalHeadquarterPosition,
        UserDistrictHeadquarterPosition
    ]
    user_id = request.user.id
    if obj is not None:
        try:
            detachment_trusted = UserDetachmentPosition.objects.get(
                headquarter_id=obj.id,
                user_id=user_id
            ).is_trusted
        except (UserDetachmentPosition.DoesNotExist, AttributeError):
            detachment_trusted = False
        try:
            headquarter_id = obj.educational_headquarter.id
            edu_trusted = UserEducationalHeadquarterPosition.objects.get(
                headquarter_id=headquarter_id,
                user_id=user_id
            ).is_trusted
        except (
                UserEducationalHeadquarterPosition.DoesNotExist, AttributeError
        ):
            edu_trusted = False
        try:
            headquarter_id = obj.local_headquarter.id
            local_trusted = UserLocalHeadquarterPosition.objects.get(
                headquarter_id=headquarter_id,
                user_id=user_id
            ).is_trusted
        except (UserLocalHeadquarterPosition.DoesNotExist, AttributeError):
            local_trusted = False
        try:
            regional_trusted = UserRegionalHeadquarterPosition.objects.get(
                headquarter_id=obj.regional_headquarter.id,
                user_id=user_id
            ).is_trusted
        except (UserRegionalHeadquarterPosition.DoesNotExist, AttributeError):
            regional_trusted = False
        try:
            headquarter_id = obj.regional_headquarter.district_headquarter.id
            district_trusted = UserDistrictHeadquarterPosition.objects.get(
                headquarter_id=headquarter_id,
                user_id=user_id
            ).is_trusted
        except (UserDistrictHeadquarterPosition.DoesNotExist, AttributeError):
            district_trusted = False
        return any([
            detachment_trusted,
            edu_trusted,
            local_trusted,
            regional_trusted,
            district_trusted
        ])
    else:
        return search_trusted_in_list(user_id, tables_for_check)


def check_trusted_for_eduhead(request, obj=None):
    """Проверка доверенного пользователя для Образовательного Штаба.

    request - запрос к эндпоинту.
    obj - штаб, к которому пользователь сделал запрос.
    Управлять Обр. штабом может любой доверенный пользователь из штабов выше.
    Функция проверяет существует ли запись о юзере
    в штабах выше и если существует, то возвращает статус доверенности.
    """

    tables_for_check = [
        UserEducationalHeadquarterPosition,
        UserLocalHeadquarterPosition,
        UserRegionalHeadquarterPosition,
        UserDistrictHeadquarterPosition
    ]
    user_id = request.user.id
    if obj is not None:
        try:
            edu_trusted = UserEducationalHeadquarterPosition.objects.get(
                headquarter_id=obj.id,
                user_id=user_id
            ).is_trusted
        except (
                UserEducationalHeadquarterPosition.DoesNotExist, AttributeError
        ):
            edu_trusted = False
        try:
            headquarter_id = obj.local_headquarter.id
            local_trusted = UserLocalHeadquarterPosition.objects.get(
                headquarter_id=headquarter_id,
                user_id=user_id
            ).is_trusted
        except (UserLocalHeadquarterPosition.DoesNotExist, AttributeError):
            local_trusted = False
        try:
            regional_trusted = UserRegionalHeadquarterPosition.objects.get(
                headquarter_id=obj.regional_headquarter.id,
                user_id=user_id
            ).is_trusted
        except (
                UserRegionalHeadquarterPosition.DoesNotExist, AttributeError
        ):
            regional_trusted = False
        try:
            head_id = obj.regional_headquarter.district_headquarter.id
            district_trusted = UserDistrictHeadquarterPosition.objects.get(
                headquarter_id=head_id,
                user_id=user_id
            ).is_trusted
        except (
                UserDistrictHeadquarterPosition.DoesNotExist, AttributeError
        ):
            district_trusted = False
        return any([
            edu_trusted,
            local_trusted,
            regional_trusted,
            district_trusted
        ])
    else:
        return search_trusted_in_list(user_id, tables_for_check)


def check_trusted_for_localhead(request, obj=None):
    """Проверка доверенного пользователя для Местного Штаба.

    request - запрос к эндпоинту.
    obj - штаб, к которому пользователь сделал запрос.
    Управлять МШ может любой доверенный пользователь из штабов выше.
    Функция проверяет существует ли запись о юзере
    в штабах выше и если существует, то возвращает статус доверенности.
    """

    tables_for_check = [
        UserLocalHeadquarterPosition,
        UserRegionalHeadquarterPosition,
        UserDistrictHeadquarterPosition
    ]
    user_id = request.user.id
    if obj is not None:
        try:
            local_trusted = UserLocalHeadquarterPosition.objects.get(
                headquarter_id=obj.id,
                user_id=user_id
            ).is_trusted
        except (UserLocalHeadquarterPosition.DoesNotExist, AttributeError):
            local_trusted = False
        try:
            regional_trusted = UserRegionalHeadquarterPosition.objects.get(
                headquarter_id=obj.regional_headquarter.id,
                user_id=user_id
            ).is_trusted
        except (UserRegionalHeadquarterPosition.DoesNotExist, AttributeError):
            regional_trusted = False
        try:
            headquarter_id = obj.regional_headquarter.district_headquarter.id
            district_trusted = UserDistrictHeadquarterPosition.objects.get(
                headquarter_id=headquarter_id,
                user_id=user_id
            ).is_trusted
        except (UserDistrictHeadquarterPosition.DoesNotExist, AttributeError):
            district_trusted = False
        return any([
            local_trusted,
            regional_trusted,
            district_trusted
        ])
    else:
        return search_trusted_in_list(user_id, tables_for_check)


def check_trusted_for_regionalhead(request, obj=None):
    """Проверка доверенного пользователя для Регионального Штаба.

    request - запрос к эндпоинту.
    obj - штаб, к которому пользователь сделал запрос.
    Управлять РШ может любой доверенный пользователь из Окружного Штаба.
    Функция проверяет существует ли запись о юзере
    в Окружном штабе и если существует, то возвращает статус доверенности.
    """

    user_id = request.user.id
    if obj is not None:
        try:
            regional_trusted = UserRegionalHeadquarterPosition.objects.get(
                headquarter_id=obj.id,
                user_id=user_id
            ).is_trusted
        except (UserRegionalHeadquarterPosition.DoesNotExist, AttributeError):
            regional_trusted = False
        try:
            district_trusted = UserDistrictHeadquarterPosition.objects.get(
                headquarter_id=obj.district_headquarter.id,
                user_id=user_id
            ).is_trusted
        except (UserDistrictHeadquarterPosition.DoesNotExist, AttributeError):
            district_trusted = False
    else:
        try:
            regional_trusted = UserRegionalHeadquarterPosition.objects.get(
                user_id=user_id
            ).is_trusted
        except (UserRegionalHeadquarterPosition.DoesNotExist, AttributeError):
            regional_trusted = False
        try:
            district_trusted = UserDistrictHeadquarterPosition.objects.get(
                user_id=user_id
            ).is_trusted
        except (UserDistrictHeadquarterPosition.DoesNotExist, AttributeError):
            district_trusted = False
    return any([
        regional_trusted,
        district_trusted
    ])


def check_trusted_for_districthead(request, obj=None):
    """Проверка доверенного пользователя для Окружного Штаба.

    request - запрос к эндпоинту.
    obj - штаб, к которому пользователь сделал запрос.
    Функция проверяет существует ли запись о юзере
    в Окружном штабе и если существует, то возвращает статус доверенности.
    """

    user_id = request.user.id
    if obj is not None:
        try:
            return UserDistrictHeadquarterPosition.objects.get(
                headquarter_id=obj.id,
                user_id=user_id
            ).is_trusted
        except (UserDistrictHeadquarterPosition.DoesNotExist, AttributeError):
            return False
    else:
        try:
            return UserDistrictHeadquarterPosition.objects.get(
                user_id=user_id
            ).is_trusted
        except (UserDistrictHeadquarterPosition.DoesNotExist, AttributeError):
            return False


def check_trusted_for_centralhead(request):
    """Проверка доверенного пользователя для Центрального Штаба.

    request - запрос к эндпоинту.
    Функция проверяет существует ли запись о юзере
    в Центральном штабе и если существует, то возвращает статус доверенности.
    """

    request_user_id = request.user.id
    try:
        return UserCentralHeadquarterPosition.objects.get(
            user_id=request_user_id
        ).is_trusted
    except (
            UserCentralHeadquarterPosition.DoesNotExist,
            AttributeError
    ):
        return False


def check_roles_for_edit(request, roles_models: dict):
    """Проверка нескольких ролей.

    Аргумент  'roles_models' - словарь.
    Ключ - должность пользователя, для которой функция вернет True.
    models - список моделей 'Члены отряда/штаба',
    в которых проверяем должность пользователя из списка выше.
    """
    for role, model in roles_models.items():
        if check_role_get(request, model, role):
            return True
    return False


def check_trusted_in_headquarters(request, roles_models: dict, obj):
    """Проверка на наличие флага 'доверенный пользователь'.

    Проверка производится по моделям, указанным в словаре 'roles_models'
    """

    for _, model in roles_models.items():
        if check_trusted_user(request, model, obj):
            return True


def get_headquarter_users_positions_queryset(self,
                                             headquarter_instance,
                                             headquarter_position_instance):
    """
    Получение отфильтрованного запроса для должностей пользователей внутри
    конкретного штаба.

    Эта функция возвращает запрос для должностей пользователей внутри
    указанного штаба.
    Она предназначена для использования внутри viewset'ов для фильтрации и
    получения должностей пользователей
    на основе предоставленных `headquarter_instance` и
    `headquarter_position_instance`.

    Параметры:
    - `self`: Экземпляр viewset'а, который вызывает эту функцию.
    - `headquarter_instance`: Класс модели для штаба (например,
       CentralHeadquarter).
    - `headquarter_position_instance`: Класс модели для должности в штабе (
    например, UserCentralHeadquarterPosition).

    Возвращает:
    - Отфильтрованный запрос для должностей пользователей в указанном штабе.

    Пример использования внутри viewset'а:
    ```
    queryset = self.get_headquarter_users_positions(
        CentralHeadquarter, UserCentralHeadquarterPosition
    )
    return self.filter_by_name(queryset)
    ```
    """

    headquarter_id = self.kwargs.get('pk')
    headquarter = get_object_or_404(headquarter_instance, id=headquarter_id)
    queryset = headquarter_position_instance.objects.filter(
        headquarter=headquarter
    )
    return self.filter_by_name(queryset)


def get_user(self):
    user_id = self.kwargs.get('pk', None)
    user = get_object_or_404(
        RSOUser, id=user_id
    ) if user_id else self.request.user
    return user


def get_user_by_id(id):
    user = get_object_or_404(
        RSOUser, id=id
    )
    return user


def text_to_lines(text, proportion):
    """Функция разбивает текст на строки по заданной доле ширины."""

    text_length = len(text)
    text_list = text.split()
    lines = []
    line = ''
    for word in text_list:
        if len(line) + len(word) > text_length * proportion:
            lines.append(line)
            line = word + ' '
        else:
            line += word + ' '
    lines.append(line)
    return lines


def create_and_return_archive(files: dict):
    """Функция создает архив и возвращает его с указанными файлами."""

    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, 'w') as archive:
        for file_name, file_content in files.items():
            archive.writestr(file_name, file_content)

    archive_buffer.seek(0)
    response = HttpResponse(
        archive_buffer.read(), content_type='application/zip'
    )
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f'certs_{current_datetime}.zip'
    response['Content-Disposition'] = (
        f'attachment; filename={filename}'
    )
    return response


def get_is_trusted(obj, model):
    """Получение флага 'доверенный пользователь'.

    Проверка производится по модели, указанной в параметре `model`.
    Если юзер доверенный, то возвращается id штаба/отряда.
    Если не доверенный, то False.
    Если юзера нет в штабе/отряде, то None.
    """
    try:
        result = model.objects.filter(
            user_id=obj.id
        ).select_related('user').first()
        is_trusted = result.is_trusted
        model_id = result.headquarter_id
    except (model.DoesNotExist, AttributeError):
        is_trusted = None
    if is_trusted:
        return model_id
    return is_trusted


def get_regional_headquarters_if_commander(user):
    """Получение региональных штабов пользователя если он командир."""
    try:
        reg_headquarter = RegionalHeadquarter.objects.get(commander=user)
        return reg_headquarter
    except Exception:
        return None


def is_regional_commander(user):
    """Проверяет, является ли пользователь командиром
    регионального штаба или администратором.
    """
    check_regional_commander = get_regional_headquarters_if_commander(user)
    return user.is_authenticated and check_regional_commander


def get_detachment_commander_num(user) -> int | None:
    """Получение id отряда, в котором юзер командир."""

    try:
        detachment_commander_num = Detachment.objects.get(
            commander=user
        ).id
    except (
            Detachment.DoesNotExist, AttributeError, ValueError,
            Detachment.MultipleObjectsReturned
    ):
        return None
    return detachment_commander_num


def get_regional_hq_commander_num(user) -> int | None:
    """Получение id регионального штаба, в котором юзер командир."""

    try:
        reghq_commander_num = RegionalHeadquarter.objects.get(
            commander=user
        ).id
    except (
            RegionalHeadquarter.DoesNotExist, AttributeError, ValueError,
            RegionalHeadquarter.MultipleObjectsReturned
    ):
        return None
    return reghq_commander_num


def get_district_hq_commander_num(user) -> int | None:
    """Получение id Окружного штаба, в котором юзер командир."""

    try:
        district_headquarter_commander_num = DistrictHeadquarter.objects.get(
            commander=user
        ).id
    except (
            DistrictHeadquarter.DoesNotExist, AttributeError, ValueError,
            DistrictHeadquarter.MultipleObjectsReturned
    ):
        return None
    return district_headquarter_commander_num


def get_central_hq_commander_num(user) -> int | None:
    """Получение id Центрального штаба, в котором юзер командир."""

    try:
        central_headquarter_commander_num = CentralHeadquarter.objects.get(
            commander=user
        ).id
    except (
            CentralHeadquarter.DoesNotExist, AttributeError, ValueError,
            CentralHeadquarter.MultipleObjectsReturned
    ):
        return None
    return central_headquarter_commander_num


def get_regional_hq_commander_num(user) -> int | None:
    """Получение id регионального штаба, в котором юзер командир."""

    try:
        reghq_commander_num = RegionalHeadquarter.objects.get(
            commander=user
        ).id
    except (
            RegionalHeadquarter.DoesNotExist, AttributeError, ValueError,
            RegionalHeadquarter.MultipleObjectsReturned
    ):
        return None
    return reghq_commander_num


def is_commander_this_detachment(user, detachment):
    """Проверяет, является ли пользователь командиром отряда."""
    return user.is_authenticated and detachment.commander == user


def is_regional_commissioner(user):
    """Проверяет, является ли пользователь комиссаром рег штаба."""
    if not user.is_authenticated:
        return False
    try:
        position_name = user.userregionalheadquarterposition.position.name
    except (UserRegionalHeadquarterPosition.DoesNotExist, AttributeError):
        return False
    return position_name == 'Комиссар' or user.is_staff


def is_central_event_master(user):
    """
    Проверяет, является ли пользователь начальником
    отдела реализации мероприятий по
    профессиональному обучению участников
    студенческих отрядов ЦШ.
    """
    if not user.is_authenticated:
        return False
    try:
        position_name = user.usercentralheadquarterposition.position.name
    except UserCentralHeadquarterPosition.DoesNotExist:
        return False
    return (
            'Начальник отдела реализации мероприятий по '
            'профессиональному обучению участников студенческих отрядов ЦШ' in position_name or user.is_staff
    )


def get_detachment_tandem(user, competition_id):
    """
    Возвращает отряд-участник заявки тандем, в котором юзер командир.
    Если юзер не командир, то возвращает 404.
    Если юзер командир отряда, но его отряд не участвует в мероприятии
    как один из тандем участников, то функция возвращает None.

    :param user: объект пользователя, например request.user
    :param competition_id: id мероприятия
    """
    detachment = get_object_or_404(
        Detachment,
        commander=user
    )
    if CompetitionParticipants.objects.filter(
            Q(detachment=detachment) | Q(junior_detachment=detachment) &
            Q(detachment__isnull=False) &
            Q(competition_id=competition_id)
    ).exists():
        return detachment


def get_detachment_start(user, competition_id):
    """
    Возвращает отряд-участник заявки старт, в котором юзер командир.
    Если юзер не командир, то возвращает 404.
    Если юзер командир отряда, но его отряд не участвует в мероприятии
    как старт-участник, то функция возвращает None.

    :param user: объект пользователя, например request.user
    :param competition_id: id мероприятия
    """
    detachment = get_object_or_404(
        Detachment,
        commander=user
    )
    if CompetitionParticipants.objects.filter(
            Q(junior_detachment=detachment) &
            Q(detachment__isnull=True) &
            Q(competition_id=competition_id)
    ).exists():
        return detachment


def is_competition_participant(detachment, competition):
    """Проверяет, является ли отряд участником конкурса."""
    return CompetitionParticipants.objects.filter(
        Q(competition=competition, detachment=detachment) |
        Q(competition=competition, junior_detachment=detachment)
    ).exists()


def get_events_data(request):
    if isinstance(request.data, QueryDict):
        data_dict = {}
        for key, value in request.data.lists():
            match = re.match(r'participation_data\[(\d+)\]\[(\w+)\]\[(\d+)\]\[(\w+)\]', key)
            if match:
                index, field_name, sub_index, sub_field_name = match.groups()
                index = int(index)
                link_dict = {sub_field_name: value[0] if len(value) == 1 else value}
                if data_dict.get(index, {}).get(field_name) is None:
                    data_dict[index][field_name] = []
                    data_dict[index][field_name].append(link_dict)
                else:
                    data_dict[index][field_name].append(link_dict)
            else:
                match = re.match(r'participation_data\[(\d+)\]\[(\w+)\]', key)
                if match:
                    index, field_name = match.groups()
                    index = int(index)
                    if index not in data_dict:
                        data_dict[index] = {}
                    data_dict[index][field_name] = value[0] if len(value) == 1 else value

        events_data = list(data_dict.values())

        for i, participant in enumerate(events_data):
            file_key = f'participation_data[{i}][certificate_scans]'
            if file_key in request.FILES:
                participant['certificate_scans'] = request.FILES[file_key]

        return events_data


def get_user_position_at_level(headquarter_model, position_model, user_id: int) -> dict | None:
    commander_in_headquarter = headquarter_model.objects.filter(commander_id=user_id).first()
    if commander_in_headquarter:
        return {
            'level': headquarter_model.__name__,
            'headquarter_id': commander_in_headquarter.id,
            'position': 'Командир'
        }
    else:
        user_headquarter_position = position_model.objects.filter(user_id=user_id).first()
        if user_headquarter_position:
            return {
                'level': user_headquarter_position.headquarter.__class__.__name__,
                'headquarter_id': user_headquarter_position.headquarter.id,
                'position': user_headquarter_position.position.name
            }


def get_user_detachment_position(user):
    if Detachment.objects.filter(commander=user).exists():
        return "Командир"
    else:
        user_detachment_position = getattr(user, 'userdetachmentposition', None)
        return user_detachment_position.position.name if user_detachment_position and hasattr(
            user_detachment_position, 'position'
        ) else "-"


def get_user_detachment(user):
    detachment = Detachment.objects.filter(commander=user).first()
    if detachment:
        return detachment.name
    else:
        detachment_position = getattr(user, 'userdetachmentposition', None)
        return detachment_position.headquarter.name if detachment_position and hasattr(
            detachment_position,
            'headquarter'
        ) else None


def get_calculation(report, report_number):
    """Функция вызова калькуляции очков при совпадении номера показателя."""

    match report_number:
        case '5':
            return calculate_r5_score(report)
        case '':
            return None
    return None


class RequestHandler(object):
    """
    Handles standard Django requests, providing necessary attributes for logging.
    """

    def __init__(self, request):
        self.request = request

    @property
    def method(self):
        """
        Returns the HTTP method of the request.
        """
        try:
            return self.request.method
        except Exception as e:
            print(f"Error retrieving request method: {e}")
            return None

    @property
    def data(self):
        """
        Returns None for Django requests (DRF requests are handled separately).
        """
        return None

    @property
    def query_params(self):
        """
        Returns sanitized query parameters, with secrets removed.
        """
        try:
            return remove_secrets(self.request.GET)
        except Exception as e:
            print(f"Error retrieving query parameters: {e}")
            return {}

    @property
    def full_path(self):
        """
        Returns the full request path.
        """
        try:
            return self.request.get_full_path()
        except Exception as e:
            print(f"Error retrieving full request path: {e}")
            return ""

    @property
    def request_id(self):
        """
        Returns the unique request ID.
        """
        try:
            return get_request_id()
        except Exception as e:
            print(f"Error retrieving request ID: {e}")
            return None


class DRFRequestHandler(RequestHandler):
    """
    Handles Django REST Framework requests, providing necessary attributes for logging.
    """

    @property
    def data(self):
        """
        Returns sanitized request data, with secrets removed.
        """
        try:
            return remove_secrets(self.request.data)
        except Exception as e:
            print(f"Error retrieving request data: {e}")
            return {}

    @property
    def query_params(self):
        """
        Returns query parameters from DRF request.
        """
        try:
            return self.request.query_params
        except Exception as e:
            print(f"Error retrieving DRF query parameters: {e}")
            return {}


class ResponseHandler(object):
    """
    Handles the response for both Django and DRF requests, extracting status and data for logging.
    """

    def __init__(self, response):
        self.response = response

    @property
    def status_code(self):
        """
        Returns the HTTP status code of the response.
        """
        try:
            return self.response.status_code
        except Exception as e:
            print(f"Error retrieving response status code: {e}")
            return None

    @property
    def data(self):
        """
        Returns sanitized response data, with secrets removed.
        """
        try:
            data = getattr(self.response, 'data', None)
            if isinstance(data, dict):
                return remove_secrets(data)
            return data
        except Exception as e:
            print(f"Error retrieving response data: {e}")
            return None


class CustomRequestLogEntry(object):
    """
    Custom request log entry class to handle logging of requests and responses with error handling.
    """

    django_request_handler = RequestHandler
    drf_request_handler = DRFRequestHandler
    response_handler = ResponseHandler

    _user = None
    _drf_request = None

    def __init__(self, request, view_func):
        self.django_request = request
        self.view_func = view_func
        self.view_class = getattr(view_func, 'cls', None)
        self.view_obj = None
        self._initialized_at = time.time()

    def finalize(self, response):
        """
        Finalizes the request log entry, processes the request and response, and stores the log entry.
        """
        try:
            renderer_context = getattr(response, 'renderer_context', {})

            self.view_obj = renderer_context.get('view')

            if not self.drf_request:
                self.drf_request = renderer_context.get('request')

            if self.drf_request:
                self.request = self.drf_request_handler(self.drf_request)
            else:
                self.request = self.django_request_handler(self.django_request)

            self.response = self.response_handler(response)
            self.store()
        except Exception as e:
            print(f"Error during log finalization: {e}")

    def store(self):
        """
        Stores the log entry by calling the defined storage class.
        """
        try:
            storage = SETTINGS['STORAGE_CLASS']()
            storage.store(self)
        except Exception as e:
            print(f"Error during storing log entry: {e}")

    @property
    def user(self):
        """
        Returns the user information if the user is authenticated.
        """
        try:
            ret = {
                'id': None,
                'username': None,
            }

            user = self._user or getattr(self.django_request, 'user', None)
            if user and user.is_authenticated:
                ret['id'] = user.id
                ret['username'] = user.username

            return ret
        except Exception as e:
            print(f"Error retrieving user information: {e}")
            return {'id': None, 'username': None}

    @user.setter
    def user(self, user):
        self._user = user

    @property
    def drf_request(self):
        return self._drf_request

    @drf_request.setter
    def drf_request(self, drf_request):
        assert isinstance(drf_request, (Request, type(None)))
        self._drf_request = drf_request

    @property
    def action_name(self):
        """
        Retrieves the name of the action being performed.
        """
        try:
            if not self.view_class:
                return None
            action_names = getattr(self.view_class, 'requestlogs_action_names', {})
            try:
                return action_names[self.view_obj.action]
            except (KeyError, AttributeError):
                try:
                    return action_names[self.django_request.method.lower()]
                except KeyError:
                    pass
        except Exception as e:
            print(f"Error retrieving action name: {e}")
            return None

    @property
    def ip_address(self):
        """
        Retrieves the IP address of the client making the request.
        """
        try:
            return get_client_ip(self.django_request)
        except Exception as e:
            print(f"Error retrieving IP address: {e}")
            return None

    @property
    def timestamp(self):
        """
        Returns the current timestamp.
        """
        try:
            return timezone.now()
        except Exception as e:
            print(f"Error retrieving timestamp: {e}")
            return None

    @property
    def execution_time(self):
        """
        Returns the execution time for the request.
        """
        try:
            return datetime.timedelta(seconds=time.time() - self._initialized_at)
        except Exception as e:
            print(f"Error calculating execution time: {e}")
            return None
