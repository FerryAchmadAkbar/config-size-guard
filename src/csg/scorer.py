"""
src/csg/scorer.py — SRE Risk Evaluator
"""
from pathlib import Path
from .models import FileResult

def evaluate_risk(result: FileResult) -> None:
    base_score = 0
    correlations = []
    
    # Kalkulasi berdasarkan tingkat keparahan (Severity)
    for check in result.checks:
        if check.score >= 2:
            base_score += 12  # Fatal / Critical (Misal: Array Explosion)
        elif check.score == 1:
            base_score += 6   # Warning (Misal: Minor Size Drift)
            
        correlations.append(f"{check.check}_triggered")
            
    result.total_score = base_score
    result.correlations_triggered = correlations
    
    if base_score >= 12:
        result.verdict = "CRITICAL" # Pipeline CI/CD akan dihentikan!
    elif base_score >= 6:
        result.verdict = "WARN"     # Pipeline lolos, tapi notifikasi Slack dikirim
    else:
        result.verdict = "PASS"