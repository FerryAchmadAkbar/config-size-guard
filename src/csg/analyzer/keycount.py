import json
import statistics
from pathlib import Path
from ..models import CheckResult

def _count_keys_recursive(obj) -> int:
    if isinstance(obj, dict):
        return len(obj) + sum((_count_keys_recursive(v) for v in obj.values()))
    if isinstance(obj, list):
        return sum((_count_keys_recursive(item) for item in obj))
    return 0

def _find_list_of_dicts(obj, path: str='root', max_depth: int=6) -> list[tuple[str, list]]:
    found = []
    if max_depth <= 0:
        return found
    if isinstance(obj, list):
        if len(obj) >= 3 and all((isinstance(item, dict) for item in obj)):
            found.append((path, obj))
        else:
            for i, item in enumerate(obj[:20]):
                found.extend(_find_list_of_dicts(item, f'{path}[{i}]', max_depth - 1))
    elif isinstance(obj, dict):
        for key, val in obj.items():
            found.extend(_find_list_of_dicts(val, f'{path}.{key}', max_depth - 1))
    return found

def _analyze_list_of_dicts(data: list, path: str, cfg: dict) -> list[CheckResult]:
    if not data or not all((isinstance(item, dict) for item in data)):
        return []
    key_counts = [len(item) for item in data]
    if len(key_counts) < 3:
        return []
    median_keys = statistics.median(key_counts)
    if median_keys == 0:
        return []
    inflation_threshold = float(cfg.get('keycount', {}).get('item_key_inflation_threshold', 0.0))
    inflated_items = [c for c in key_counts if c > median_keys]
    inflation_ratio = len(inflated_items) / len(key_counts)
    max_keys = max(key_counts)
    extra_keys = max_keys - int(median_keys)
    if extra_keys < 1:
        return []
    MIN_INFLATION_RATIO = 0.05
    if inflation_ratio < MIN_INFLATION_RATIO:
        return []
    checks = []
    if inflation_ratio > inflation_threshold and inflated_items:
        checks.append(CheckResult(check='keycount_item_inflation', score=1 if extra_keys == 1 else 2, detail=f"List di '{path}' berisi {len(data)} item. Median key per item: {int(median_keys)}. {len(inflated_items)} item ({inflation_ratio:.0%}) memiliki {extra_keys} key ekstra melebihi median. Pola ini mengindikasikan field tak terduga (seperti CrowdStrike Channel File 291).", value={'median_keys': int(median_keys), 'max_keys': max_keys, 'inflated_count': len(inflated_items)}, remediation='Periksa apakah ada field baru yang ditambahkan ke schema.'))
    return checks

def analyze_keycount(filepath: Path, baseline_entry: dict | None, cfg: dict) -> list[CheckResult]:
    checks: list[CheckResult] = []
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return checks
    ext = filepath.suffix.lower()
    if baseline_entry:
        base_keys = baseline_entry.get('base_keycount', 0)
        if base_keys > 0:
            import re
            KEY_PATTERN = re.compile('(?:["\\\']?[\\w.-]+["\\\']?\\s*[:=])|(?:<[\\w.-]+>)')
            current_keys = len(KEY_PATTERN.findall(content))
            growth_ratio = current_keys / base_keys
            if growth_ratio > 2.0 and current_keys > 10:
                checks.append(CheckResult(check='abnormal_key_inflation', score=1, detail=f'Jumlah key tumbuh {growth_ratio:.2f}x dari baseline ({base_keys} → {current_keys}).', value=current_keys, remediation='Verifikasi apakah penambahan key ini disengaja.', is_delta=True))
    if ext in ('.json', '.jsonc', '.json5'):
        try:
            clean = '\n'.join((line for line in content.splitlines() if not line.strip().startswith('//')))
            parsed = json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if parsed is not None:
            for path_str, list_data in _find_list_of_dicts(parsed):
                checks.extend(_analyze_list_of_dicts(list_data, path_str, cfg))
    return checks