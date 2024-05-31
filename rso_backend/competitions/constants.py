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
                                 Q20TandemRanking)

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

COUNT_PLACES_DEADLINE = date(2024, 10, 15) + timedelta(days=1)
DEADLINE_RESPONSE = Response(
    {'error': 'Прием ответов по показателю окончен {deadline}.'},
    status=status.HTTP_400_BAD_REQUEST
)
