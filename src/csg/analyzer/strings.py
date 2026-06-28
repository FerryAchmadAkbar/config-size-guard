"""
analyzer/strings.py — IQR-Based Scanner with Configurable Safety Net
"""
import re
from pathlib import Path
from ..models import CheckResult
from ..safe_patterns import is_safe_token

_TOKEN_SPLIT = re.compile(r'[\s\'"{}\[\],:;|<>\(\)!]+')

def extract_longest_token(content: str) -> str:
    tokens = _TOKEN_SPLIT.split(content)
    return max(tokens, key=len, default="")

def analyze_strings(filepath: Path, cfg: dict, baseline_entry: dict | None) -> list[CheckResult]:
    checks = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return checks

    tokens = _TOKEN_SPLIT.split(content)
    max_unsafe_len = 0
    for t in tokens:
        if not is_safe_token(t):
            max_unsafe_len = max(max_unsafe_len, len(t))

    # 1. MINIMUM SAMPLE GUARD (Dikendalikan oleh Config YAML)
    sample_size = cfg.get("sample_size", 0)
    fallback_limit = cfg.get("fallback_string_length", 1000)

    if sample_size < 20:
        if max_unsafe_len > fallback_limit:
            checks.append(CheckResult(check="string_growth_spike", score=2, detail=f"Len: {max_unsafe_len} (Fallback Threshold)"))
        return checks

    # 2. IQR ANALYTICS (Dinamis)
    q3 = cfg.get("strings_q3", 50.0)
    iqr = cfg.get("strings_iqr", 10.0)
    if iqr == 0: iqr = 10.0

    outlier_threshold = q3 + (3 * iqr)

    if max_unsafe_len > outlier_threshold and max_unsafe_len > 50:
        checks.append(CheckResult(
            check="string_growth_spike", score=2, 
            detail=f"Len: {max_unsafe_len}, Outlier Limit: {round(outlier_threshold, 2)}"
        ))

    return checks