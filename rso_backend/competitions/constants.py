from datetime import date, timedelta
from rest_framework.response import Response
from rest_framework import status
from competitions.models import (Q1Ranking, Q1TandemRanking, Q2Ranking,
                                 Q2TandemRanking, Q3Ranking, Q3TandemRanking,
                                 Q4Ranking, Q4TandemRanking, Q5Ranking,
                                 Q5TandemRanking, Q6Ranking, Q6TandemRanking,
                                 Q7Ranking, Q7TandemRanking, Q8Ranking,
                                 Q8TandemRanking, Q9Ranking, Q9TandemRanking,
                                 Q10Ranking, Q10TandemRanking, Q11Ranking,
                                 Q11TandemRanking, Q12Ranking,
                                 Q12TandemRanking, Q13Ranking,
                                 Q13TandemRanking, Q14Ranking,
                                 Q14TandemRanking, Q15Rank, Q15TandemRank,
                                 Q16Ranking, Q16TandemRanking, Q17Ranking,
                                 Q17TandemRanking, Q18Ranking,
                                 Q18TandemRanking, Q19Ranking,
                                 Q19TandemRanking, Q20Ranking,
                                 Q20TandemRanking, Q2DetachmentReport, Q5DetachmentReport, Q6DetachmentReport,
                                 Q13DetachmentReport, Q14DetachmentReport, Q15DetachmentReport, Q17DetachmentReport,
                                 Q18DetachmentReport, Q1Report, Q12Report, Q11Report, Q10Report, Q9Report, Q8Report,
                                 Q7Report, Q16Report, Q19Report, Q20Report)

SOLO_RANKING_MODELS = [
    Q1Ranking,
    Q2Ranking,
    Q3Ranking,
    Q4Ranking,
    Q5Ranking,
    Q6Ranking,
    Q7Ranking,
    Q8Ranking,
    Q9Ranking,
    Q10Ranking,
    Q11Ranking,
    Q12Ranking,
    Q13Ranking,
    Q14Ranking,
    Q15Rank,
    Q16Ranking,
    Q17Ranking,
    Q18Ranking,
    Q19Ranking,
    Q20Ranking
]
TANDEM_RANKING_MODELS = [
    Q1TandemRanking,
    Q2TandemRanking,
    Q3TandemRanking,
    Q4TandemRanking,
    Q5TandemRanking,
    Q6TandemRanking,
    Q7TandemRanking,
    Q8TandemRanking,
    Q9TandemRanking,
    Q10TandemRanking,
    Q11TandemRanking,
    Q12TandemRanking,
    Q13TandemRanking,
    Q14TandemRanking,
    Q15TandemRank,
    Q16TandemRanking,
    Q17TandemRanking,
    Q18TandemRanking,
    Q19TandemRanking,
    Q20TandemRanking
]
DETACHMENT_REPORTS_MODELS = {
    1: Q1Report,
    2: Q2DetachmentReport,
    5: Q5DetachmentReport,
    6: Q6DetachmentReport,
    7: Q7Report,
    8: Q8Report,
    9: Q9Report,
    10: Q10Report,
    11: Q11Report,
    12: Q12Report,
    13: Q13DetachmentReport,
    14: Q14DetachmentReport,
    15: Q15DetachmentReport,
    16: Q16Report,
    17: Q17DetachmentReport,
    18: Q18DetachmentReport,
    19: Q19Report,
    20: Q20Report
}

COUNT_PLACES_DEADLINE = date(2024, 10, 15) + timedelta(days=1)

DEADLINE_RESPONSE_TEMPLATE = 'Прием ответов по показателю окончен {deadline}.'


def get_deadline_response(deadline):
    return Response(
        {'error': DEADLINE_RESPONSE_TEMPLATE.format(deadline=deadline)},
        status=status.HTTP_400_BAD_REQUEST
    )
