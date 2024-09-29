from django.db.models import signals
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from competitions.models import Q7, Q8, Q9, Q10, Q11, Q12, Q16Report, Q20Report


@receiver([post_save, post_delete], sender=Q7)
def create_score_q7(sender, instance, created=False, **kwargs):
    if created:
        pass
    else:
        if instance.is_verified:
            report = instance.detachment_report
            events = Q7.objects.filter(
                        detachment_report=report,
                        is_verified=True
            ).all()
            report.score = (
                report.score_calculation_sum(
                    events, 'number_of_participants'
                )
            )
            report.save()

            return report


@receiver([post_save, post_delete], sender=Q8)
def create_score_q8(sender, instance, created=False, **kwargs):
    if created:
        pass
    else:
        if instance.is_verified:
            report = instance.detachment_report
            events = Q8.objects.filter(
                        detachment_report=report,
                        is_verified=True
            ).all()
            report.score = (
                report.score_calculation_sum(
                    events, 'number_of_participants'
                )
            )
            report.save()

            return report


@receiver([post_save, post_delete], sender=Q9)
def create_score_q9(sender, instance, created=False, **kwargs):
    if created:
        pass
    else:
        if instance.is_verified:
            report = instance.detachment_report
            events = Q9.objects.filter(
                        detachment_report=report,
                        is_verified=True
            ).all()
            score = 0
            for event in events:
                score += 4 - event.prize_place

            report.score = score
            report.save()

            return report


@receiver([post_save, post_delete], sender=Q10)
def create_score_q10(sender, instance, created=False, **kwargs):
    if created:
        pass
    else:
        if instance.is_verified:
            report = instance.detachment_report
            events = Q10.objects.filter(
                        detachment_report=report,
                        is_verified=True
            ).all()
            score = 0
            for event in events:
                score += 4 - event.prize_place

            report.score = score
            report.save()

            return report


@receiver([post_save, post_delete], sender=Q11)
def create_score_q11(sender, instance, created=False, **kwargs):
    if created:
        pass
    else:
        if instance.is_verified:
            report = instance.detachment_report
            events = Q11.objects.filter(
                        detachment_report=report,
                        is_verified=True
            ).all()
            score = 0
            for event in events:
                score += 4 - event.prize_place

            report.score = score
            report.save()

            return report


@receiver([post_save, post_delete], sender=Q12)
def create_score_q12(sender, instance, created=False, **kwargs):
    if created:
        pass
    else:
        if instance.is_verified:
            report = instance.detachment_report
            events = Q12.objects.filter(
                        detachment_report=report,
                        is_verified=True
            ).all()
            score = 0
            for event in events:
                score += 4 - event.prize_place

            report.score = score
            report.save()

            return report
