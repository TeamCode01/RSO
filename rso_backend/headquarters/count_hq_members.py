from headquarters.models import (CentralHeadquarter, Detachment,
                                 DistrictHeadquarter, EducationalHeadquarter,
                                 LocalHeadquarter, RegionalHeadquarter,
                                 UserCentralHeadquarterPosition,
                                 UserDetachmentPosition,
                                 UserDistrictHeadquarterPosition,
                                 UserEducationalHeadquarterPosition,
                                 UserLocalHeadquarterPosition,
                                 UserRegionalHeadquarterPosition)
from questions.models import Attempt
from events.models import Event


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


def count_verified_users(headquarter):
    if isinstance(headquarter, CentralHeadquarter):
        verified_count = UserCentralHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__is_verified=True,
        ).count()
    elif isinstance(headquarter, DistrictHeadquarter):
        verified_count = UserDistrictHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__is_verified=True,
        ).count()
    elif isinstance(headquarter, RegionalHeadquarter):
        verified_count = UserRegionalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__is_verified=True,
        ).count()
    elif isinstance(headquarter, LocalHeadquarter):
        verified_count = UserLocalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__is_verified=True,
        ).count()
    elif isinstance(headquarter, EducationalHeadquarter):
        verified_count = UserEducationalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__is_verified=True,
        ).count()
    elif isinstance(headquarter, Detachment):
        verified_count = UserDetachmentPosition.objects.filter(
            headquarter=headquarter,
            user__is_verified=True,
        ).count()
    else:
        raise ValueError('Будьте внимательны :)')

    return verified_count + 1


def count_membership_fee(headquarter):
    if isinstance(headquarter, CentralHeadquarter):
        membership_fee_count = UserCentralHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
    elif isinstance(headquarter, DistrictHeadquarter):
        membership_fee_count = UserDistrictHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
    elif isinstance(headquarter, RegionalHeadquarter):
        membership_fee_count = UserRegionalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
    elif isinstance(headquarter, LocalHeadquarter):
        membership_fee_count = UserLocalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
    elif isinstance(headquarter, EducationalHeadquarter):
        membership_fee_count = UserEducationalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
    elif isinstance(headquarter, Detachment):
        membership_fee_count = UserDetachmentPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
    else:
        raise ValueError('Будьте внимательны :)')

    return membership_fee_count + 1


def count_test_membership(headquarter):
    if isinstance(headquarter, CentralHeadquarter):
        members = UserCentralHeadquarterPosition.objects.filter(headquarter=headquarter)
        test_membership_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
    elif isinstance(headquarter, DistrictHeadquarter):
        members = UserDistrictHeadquarterPosition.objects.filter(headquarter=headquarter)
        test_membership_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
    elif isinstance(headquarter, RegionalHeadquarter):
        members = UserRegionalHeadquarterPosition.objects.filter(headquarter=headquarter)
        test_membership_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
    elif isinstance(headquarter, LocalHeadquarter):
        members = UserLocalHeadquarterPosition.objects.filter(headquarter=headquarter)
        test_membership_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
    elif isinstance(headquarter, EducationalHeadquarter):
        members = UserEducationalHeadquarterPosition.objects.filter(headquarter=headquarter)
        test_membership_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
    elif isinstance(headquarter, Detachment):
        members = UserDetachmentPosition.objects.filter(headquarter=headquarter)
        test_membership_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
    else:
        raise ValueError('Будьте внимательны :)')

    return test_membership_count + 1


def count_events_organizations(headquarter):
    if isinstance(headquarter, CentralHeadquarter):
        events = Event.objects.filter(org_central_headquarter=headquarter).count()
    elif isinstance(headquarter, DistrictHeadquarter):
        events = Event.objects.filter(org_district_headquarter=headquarter).count()
    elif isinstance(headquarter, RegionalHeadquarter):
        events = Event.objects.filter(org_regional_headquarter=headquarter).count()
    elif isinstance(headquarter, LocalHeadquarter):
        events = Event.objects.filter(org_local_headquarter=headquarter).count()
    elif isinstance(headquarter, EducationalHeadquarter):
        events = Event.objects.filter(org_educational_headquarter=headquarter).count()
    elif isinstance(headquarter, Detachment):
        events = Event.objects.filter(org_detachment=headquarter).count()
    else:
        raise ValueError('Будьте внимательны :)')

    return events