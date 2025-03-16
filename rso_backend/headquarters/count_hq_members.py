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
from questions.models import Attempt
from events.models import Event, EventParticipants
from headquarters.mixins import (CentralSubCommanderIdMixin, RegionalSubCommanderIdMixin,
                                 DistrictSubCommanderIdMixin, EducationalSubCommanderIdMixin,
                                 LocalSubCommanderIdMixin, CentralSubCommanderIdMixin)
from users.models import RSOUser


def count_headquarter_participants(headquarter, user_id=None):
    sub_commanders = []

    if isinstance(headquarter, CentralHeadquarter):
        user_count = UserCentralHeadquarterPosition.objects.filter(headquarter=headquarter).count()
        sub_commanders = CentralSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, DistrictHeadquarter):
        user_count = UserDistrictHeadquarterPosition.objects.filter(headquarter=headquarter).count()
        sub_commanders = DistrictSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, RegionalHeadquarter):
        user_count = UserRegionalHeadquarterPosition.objects.filter(headquarter=headquarter).count()
        sub_commanders = RegionalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, LocalHeadquarter):
        user_count = UserLocalHeadquarterPosition.objects.filter(headquarter=headquarter).count()
        sub_commanders = LocalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, EducationalHeadquarter):
        user_count = UserEducationalHeadquarterPosition.objects.filter(headquarter=headquarter).count()
        sub_commanders = EducationalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, Detachment):
        user_count = UserDetachmentPosition.objects.filter(headquarter=headquarter).count()
    else:
        raise ValueError('Неизвестный тип штаба')

    sub_commander_count = len(sub_commanders)
    member_count = user_count + sub_commander_count + 1

    return member_count


def count_verified_users(headquarter, user_id=None):
    sub_commanders = []

    if isinstance(headquarter, CentralHeadquarter):
        verified_user_count = UserCentralHeadquarterPosition.objects.filter(
            headquarter=headquarter, user__is_verified=True).count()
        sub_commanders = CentralSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, DistrictHeadquarter):
        verified_user_count = UserDistrictHeadquarterPosition.objects.filter(
            headquarter=headquarter, user__is_verified=True).count()
        sub_commanders = DistrictSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, RegionalHeadquarter):
        verified_user_count = UserRegionalHeadquarterPosition.objects.filter(
            headquarter=headquarter, user__is_verified=True).count()
        sub_commanders = RegionalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, LocalHeadquarter):
        verified_user_count = UserLocalHeadquarterPosition.objects.filter(
            headquarter=headquarter, user__is_verified=True).count()
        sub_commanders = LocalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, EducationalHeadquarter):
        verified_user_count = UserEducationalHeadquarterPosition.objects.filter(
            headquarter=headquarter, user__is_verified=True).count()
        sub_commanders = EducationalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, Detachment):
        verified_user_count = UserDetachmentPosition.objects.filter(
            headquarter=headquarter, user__is_verified=True).count()
    else:
        raise ValueError('Неизвестный тип штаба')

    commander_ids = [cmd['id'] for cmd in sub_commanders]
    verified_sub_commander_count = RSOUser.objects.filter(id__in=commander_ids, is_verified=True).count()

    verified_count = verified_user_count + verified_sub_commander_count + 1

    return verified_count


def count_membership_fee(headquarter, user_id=None):
    sub_commanders = []

    if isinstance(headquarter, CentralHeadquarter):
        membership_fee_users_count = UserCentralHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
        sub_commanders = CentralSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, DistrictHeadquarter):
        membership_fee_users_count = UserDistrictHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
        sub_commanders = DistrictSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, RegionalHeadquarter):
        membership_fee_users_count = UserRegionalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
        sub_commanders = RegionalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, LocalHeadquarter):
        membership_fee_users_count = UserLocalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
        sub_commanders = LocalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, EducationalHeadquarter):
        membership_fee_users_count = UserEducationalHeadquarterPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
        sub_commanders = EducationalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, Detachment):
        membership_fee_users_count = UserDetachmentPosition.objects.filter(
            headquarter=headquarter,
            user__membership_fee=True,
        ).count()
    else:
        raise ValueError('Неизвестный тип штаба')

    commander_ids = [cmd['id'] for cmd in sub_commanders]
    membership_fee_sub_commanders_count = RSOUser.objects.filter(id__in=commander_ids, membership_fee=True).count()
    membership_fee_count = membership_fee_users_count + membership_fee_sub_commanders_count + 1

    return membership_fee_count 


def count_test_membership(headquarter, user_id=None):
    sub_commanders = []

    if isinstance(headquarter, CentralHeadquarter):
        members = UserCentralHeadquarterPosition.objects.filter(headquarter=headquarter)
        test_membership_users_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
        sub_commanders = CentralSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, DistrictHeadquarter):
        members = UserDistrictHeadquarterPosition.objects.filter(headquarter=headquarter)
        test_membership_users_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
        sub_commanders = DistrictSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, RegionalHeadquarter):
        members = UserRegionalHeadquarterPosition.objects.filter(headquarter=headquarter)
        test_membership_users_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
        sub_commanders = RegionalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, LocalHeadquarter):
        members = UserLocalHeadquarterPosition.objects.filter(headquarter=headquarter)
        test_membership_users_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
        sub_commanders = LocalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, EducationalHeadquarter):
        members = UserEducationalHeadquarterPosition.objects.filter(headquarter=headquarter)
        test_membership_users_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
        sub_commanders = EducationalSubCommanderIdMixin().get_sub_commanders(headquarter, user_id)
    elif isinstance(headquarter, Detachment):
        members = UserDetachmentPosition.objects.filter(headquarter=headquarter)
        test_membership_users_count = Attempt.objects.filter(
            user__in=members.values_list('user', flat=True),
            category=Attempt.Category.SAFETY,
            score__gt=60
        ).count()
    else:
        raise ValueError('Будьте внимательны :)')

    commander_ids = [cmd['id'] for cmd in sub_commanders]
    test_membership_sub_commanders_count = Attempt.objects.filter(
        user__in=commander_ids,
        category=Attempt.Category.SAFETY,
        score__gt=60
    ).count()
    test_membership_count = test_membership_users_count + test_membership_sub_commanders_count + 1

    return test_membership_count 


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


def count_events_participants(headquarter):
    if isinstance(headquarter, CentralHeadquarter):
        events = Event.objects.filter(org_central_headquarter=headquarter)
    elif isinstance(headquarter, DistrictHeadquarter):
        events = Event.objects.filter(org_district_headquarter=headquarter)
    elif isinstance(headquarter, RegionalHeadquarter):
        events = Event.objects.filter(org_regional_headquarter=headquarter)
    elif isinstance(headquarter, LocalHeadquarter):
        events = Event.objects.filter(org_local_headquarter=headquarter)
    elif isinstance(headquarter, EducationalHeadquarter):
        events = Event.objects.filter(org_educational_headquarter=headquarter)
    elif isinstance(headquarter, Detachment):
        events = Event.objects.filter(org_detachment=headquarter)
    else:
        raise ValueError('Будьте внимательны :)')
    
    event_participants_count = EventParticipants.objects.filter(event__in=events).count()
    
    return event_participants_count


def get_hq_participants_15_september(detachment):
    inst = September15Participant.objects.filter(detachment=detachment).last()
    return 1 if not inst else inst.participants_number


def get_hq_members_15_september(detachment):
    detachment_members =  September15Participant.objects.filter(detachment=detachment).last()
    return 0 if not detachment_members else detachment_members.members_number
