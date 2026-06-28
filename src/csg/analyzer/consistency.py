import re
from typing import Any
from ..models import CheckResult
_COUNT_FIELD_RE = re.compile('(total|count|num|size|length|n)[\\W_]*(records?|entries|items?|features?|rules?|services?|keys?|nodes?|rows?)|(records?|entries|items?|features?|rules?|services?)[\\W_]*(total|count|num|size|length)', re.IGNORECASE)
_ERROR_FLAG_RE = re.compile('(exceeded|overflow|error|fail|corrupt|timeout|lag|degraded|invalid|broken|crash|conflict|inconsistent|sync_error)', re.IGNORECASE)
_LIMIT_FIELD_RE = re.compile('(limit|max|capacity|threshold|cap)', re.IGNORECASE)
_ERROR_STRING_PATTERN = re.compile('^(SYNC_ERROR|BACKUP\\.RESTORED|PARTIAL\\.RESTORE|INCONSISTENT|DEGRADED|CORRUPTED|FAILED|CONFLICT|UNKNOWN|CRASH|OVERFLOW|TIMEOUT|INVALID|BROKEN)$', re.IGNORECASE)

def _find_arrays(data: Any, path: str='root') -> list[tuple[str, list]]:
    results: list[tuple[str, list]] = []
    if isinstance(data, list) and len(data) > 0:
        results.append((path, data))
        for i, item in enumerate(data):
            results.extend(_find_arrays(item, f'{path}[{i}]'))
    elif isinstance(data, dict):
        for k, v in data.items():
            results.extend(_find_arrays(v, f'{path}.{k}'))
    return results

def _find_numeric_fields(data: Any, path: str='root') -> list[tuple[str, str, int]]:
    results: list[tuple[str, str, int]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            field_path = f'{path}.{k}'
            if isinstance(v, int) and (not isinstance(v, bool)):
                if _COUNT_FIELD_RE.search(k):
                    results.append((field_path, k, v))
                else:
                    results.extend(_find_numeric_fields(v, field_path))
            elif isinstance(v, (dict, list)):
                results.extend(_find_numeric_fields(v, field_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            results.extend(_find_numeric_fields(item, f'{path}[{i}]'))
    return results

def _find_error_flags(data: Any, path: str='root') -> list[tuple[str, str, Any]]:
    results: list[tuple[str, str, Any]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            field_path = f'{path}.{k}'
            if isinstance(v, bool) and v is True:
                if _ERROR_FLAG_RE.search(k):
                    results.append((field_path, k, v))
            elif isinstance(v, str) and _ERROR_STRING_PATTERN.match(v.strip()):
                results.append((field_path, k, v))
            elif isinstance(v, (dict, list)):
                results.extend(_find_error_flags(v, field_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            results.extend(_find_error_flags(item, f'{path}[{i}]'))
    return results

def analyze_consistency(data: Any) -> list[CheckResult]:
    if data is None or isinstance(data, str):
        return []
    checks: list[CheckResult] = []
    numeric_fields = _find_numeric_fields(data)
    arrays = _find_arrays(data)
    for field_path, field_name, declared_count in numeric_fields:
        if declared_count <= 0:
            continue
        field_parent = '.'.join(field_path.split('.')[:-1])
        closest_array: tuple[str, list] | None = None
        closest_distance = float('inf')
        for arr_path, arr_data in arrays:
            arr_parent = '.'.join(arr_path.split('.')[:-1])
            if arr_parent == field_parent or arr_path.startswith(field_parent):
                dist = abs(len(arr_path) - len(field_path))
                if dist < closest_distance:
                    closest_distance = dist
                    closest_array = (arr_path, arr_data)
        if closest_array is None:
            continue
        arr_path, arr_data = closest_array
        actual_count = len(arr_data)
        if actual_count == 0:
            continue
        mismatch_ratio = abs(declared_count - actual_count) / declared_count
        if mismatch_ratio >= 0.9:
            checks.append(CheckResult(check='metadata_count_mismatch_critical', score=2, detail=f"Inkonsistensi kritis: field '{field_name}' mendeklarasikan {declared_count} item, tapi array '{arr_path}' hanya berisi {actual_count} item ({mismatch_ratio:.0%} mismatch). Kemungkinan truncation atau partial overwrite.", value={'declared': declared_count, 'actual': actual_count, 'mismatch_ratio': round(mismatch_ratio, 3)}, remediation='Verifikasi integritas file. Kemungkinan file ini di-replace dengan versi yang lebih lama atau tidak lengkap.'))
        elif mismatch_ratio >= 0.5:
            checks.append(CheckResult(check='metadata_count_mismatch_warn', score=1, detail=f"Field '{field_name}' mendeklarasikan {declared_count} item tapi array aktual berisi {actual_count} item ({mismatch_ratio:.0%} mismatch).", value={'declared': declared_count, 'actual': actual_count, 'mismatch_ratio': round(mismatch_ratio, 3)}, remediation='Periksa konsistensi antara metadata dan konten file.'))
    if isinstance(data, dict):
        limit_fields = {k: v for k, v in data.items() if isinstance(v, int) and (not isinstance(v, bool)) and _LIMIT_FIELD_RE.search(k)}
        count_fields = {k: v for k, v in data.items() if isinstance(v, int) and (not isinstance(v, bool)) and _COUNT_FIELD_RE.search(k)}
        for lk, lv in limit_fields.items():
            for ck, cv in count_fields.items():
                if lv > 0:
                    if cv > lv:
                        excess_ratio = (cv - lv) / lv
                        score = 2 if excess_ratio >= 0.1 else 1
                        checks.append(CheckResult(check='hard_limit_exceeded', score=score, detail=f"Field '{ck}' bernilai {cv} melebihi limit yang dideklarasikan '{lk}': {lv} (+{excess_ratio:.0%} di atas batas).", value={'count_field': ck, 'count_value': cv, 'limit_field': lk, 'limit_value': lv}, remediation='File ini melebihi batas yang dikonfigurasi. Propagasi file ini kemungkinan menyebabkan error downstream.'))
                    else:
                        proximity = cv / lv
                        if 0.5 <= proximity <= 1.0:
                            checks.append(CheckResult(check='approaching_hard_limit', score=1, detail=f"Field '{ck}' bernilai {cv}, mencapai {proximity:.0%} dari limit '{lk}': {lv}. Pantau pertumbuhan lebih lanjut.", value={'proximity_ratio': round(proximity, 3)}, remediation='File mendekati batas kapasitas yang dikonfigurasi.'))
    error_flags = _find_error_flags(data)
    if error_flags:
        flag_summary = ', '.join((f"'{name}'=True" for _, name, _ in error_flags[:5]))
        if len(error_flags) > 5:
            flag_summary += f' (+{len(error_flags) - 5} lainnya)'
        score = 2 if len(error_flags) >= 2 else 1
        checks.append(CheckResult(check='error_state_flags_active', score=score, detail=f'Ditemukan {len(error_flags)} field error/warning aktif (True) di dalam file: {flag_summary}. File ini mungkin di-generate saat sistem sedang dalam kondisi degraded.', value={'active_flags': [name for _, name, _ in error_flags]}, remediation='Periksa apakah file ini di-generate saat sistem mengalami gangguan. File konfigurasi dari kondisi error tidak seharusnya dipropagasikan.'))
    return checks