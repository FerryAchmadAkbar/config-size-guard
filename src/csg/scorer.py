from pathlib import Path
from .models import FileResult

def evaluate_risk(result: FileResult) -> None:
    base_score = 0
    correlations = []
    for check in result.checks:
        if check.score >= 2:
            base_score += 12
        elif check.score == 1:
            base_score += 6
        correlations.append(f'{check.check}_triggered')
    result.total_score = base_score
    result.correlations_triggered = correlations
    if base_score >= 12:
        result.verdict = 'CRITICAL'
    elif base_score >= 6:
        result.verdict = 'WARN'
    else:
        result.verdict = 'PASS'