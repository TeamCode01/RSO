from competitions.models import September15Participant
from headquarters.models import (CentralHeadquarter, Detachment,
                                 DistrictHeadquarter, EducationalHeadquarter,
                                 LocalHeadquarter, RegionalHeadquarter,
                                 UserCentralHeadquarterPosition,
                                 UserDetachmentPosition,
                                 UserDistrictHeadquarterPosition,
                                 UserEducationalHeadquarterPosition,
                                 UserLocalHeadquarterPosition,
                                 UserRegionalHeadquarterPosition)


def count_headquarter_participants(headquarter):
    """
    Подсчитывает количество участников данного штаба и добавляет 1 для учёта командира.

    Параметры:
    headquarter: Объект штаба (CentralHeadquarter, DistrictHeadquarter,
                 RegionalHeadquarter, LocalHeadquarter, EducationalHeadquarter или Detachment).

    Возвращает:
    int: Общее количество участников, включая командира.
    """
    if isinstance(headquarter, CentralHeadquarter):
        member_count = UserCentralHeadquarterPosition.objects.filter(
            headquarter=headquarter,
        ).count()
    elif isinstance(headquarter, DistrictHeadquarter):
        member_count = UserDistrictHeadquarterPosition.objects.filter(
            headquarter=headquarter,
        ).count()
    elif isinstance(headquarter, RegionalHeadquarter):
        member_count = UserRegionalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
        ).count()
    elif isinstance(headquarter, LocalHeadquarter):
        member_count = UserLocalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
        ).count()
    elif isinstance(headquarter, EducationalHeadquarter):
        member_count = UserEducationalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
        ).count()
    elif isinstance(headquarter, Detachment):
        member_count = UserDetachmentPosition.objects.filter(
            headquarter=headquarter,
        ).count()
    else:
        raise ValueError('Будьте внимательны :)')

    return member_count + 1


def get_hq_participants_15_september(detachment):
     inst = September15Participant.objects.filter(detachment=detachment).last()
     return 1 if not inst else inst.participants_number
