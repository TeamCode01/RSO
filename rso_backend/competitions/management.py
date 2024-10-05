from datetime import date
import traceback

from users.models import UserMembershipLogs
from competitions.models import September15Participant



def count_september_30_members_number():
    verifications_after_15 = UserMembershipLogs.objects.filter(
        date__gt=date(2024, 9, 15)
    )

    for verification in verifications_after_15:
        try:
            user_detachment_position = verification.user.userdetachmentpositions
        except Exception as e:
            print(traceback.format_exc())
        try:
            september_15_inst = September15Participant.objects.get(
                detachment=user_detachment_position.headquarter
            )
        except September15Participant.DoesNotExist:
            continue
        print(
            f'Нашли верифицированного юзера {verification.user} для отряда '
            f'{user_detachment_position.headquarter}. Обновляем значение оплативших чл. взнос '
            f'{september_15_inst.members_number} на 1'
        )
        september_15_inst.members_number += 1
        september_15_inst.save()