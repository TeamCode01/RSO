import datetime


def current_year():
    return datetime.datetime.now().year


def get_last_rcompetition_id():
    from .models import RCompetition
    last_r_competition = RCompetition.objects.last()
    return last_r_competition.id if last_r_competition else None
