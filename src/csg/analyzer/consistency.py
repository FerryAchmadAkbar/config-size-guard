"""
analyzer/consistency.py — Internal Consistency Analyzer

Memeriksa konsistensi INTERNAL file tanpa membutuhkan baseline,
peer group, atau riwayat apapun. Cocok untuk zero-day detection.

Tiga jenis pemeriksaan:
  1. Count-Content Mismatch : field yang mengklaim jumlah tertentu
                              tidak cocok dengan array aktualnya
  2. Hard Limit Exceeded    : field count melampaui field limit/max
                              yang dideklarasikan dalam file yang sama
  3. Error State Flag       : field boolean yang namanya mengindikasikan
                              kondisi error/warning terset ke True

Prinsip robustness: jika file tidak bisa di-parse atau struktur tidak
dikenali, analyzer ini silent skip — tidak pernah menghasilkan false
positive karena gagal membaca file.
"""
import re
from typing import Any

from ..models import CheckResult

# ── Regex pattern ─────────────────────────────────────────────────────────────

# Nama field yang mengindikasikan jumlah/total
# Contoh: total_records, feature_count, num_entries, record_count
_COUNT_FIELD_RE = re.compile(
    r"(total|count|num|size|length|n)[\W_]*(records?|entries|items?|"
    r"features?|rules?|services?|keys?|nodes?|rows?)|"
    r"(records?|entries|items?|features?|rules?|services?)[\W_]*"
    r"(total|count|num|size|length)",
    re.IGNORECASE,
)

# Nama field yang mengindikasikan kondisi error/limit/overflow
# Contoh: limit_exceeded, gc_lag_detected, overflow_warning, sync_error
_ERROR_FLAG_RE = re.compile(
    r"(exceeded|overflow|error|fail|corrupt|timeout|lag|degraded|"
    r"invalid|broken|crash|conflict|inconsistent|sync_error)",
    re.IGNORECASE,
)

# Nama field yang mengindikasikan batas/kapasitas
_LIMIT_FIELD_RE = re.compile(
    r"(limit|max|capacity|threshold|cap)",
    re.IGNORECASE,
)

_ERROR_STRING_PATTERN = re.compile(
    r"^(SYNC_ERROR|BACKUP\.RESTORED|PARTIAL\.RESTORE|INCONSISTENT|"
    r"DEGRADED|CORRUPTED|FAILED|CONFLICT|UNKNOWN|CRASH|OVERFLOW|"
    r"TIMEOUT|INVALID|BROKEN)$",
    re.IGNORECASE,
)


# ── Traversal helpers ─────────────────────────────────────────────────────────

def _find_arrays(data: Any, path: str = "root") -> list[tuple[str, list]]:
    """Temukan semua array/list di dalam config secara rekursif."""
    results: list[tuple[str, list]] = []
    if isinstance(data, list) and len(data) > 0:
        results.append((path, data))
        for i, item in enumerate(data):
            results.extend(_find_arrays(item, f"{path}[{i}]"))
    elif isinstance(data, dict):
        for k, v in data.items():
            results.extend(_find_arrays(v, f"{path}.{k}"))
    return results


def _find_numeric_fields(data: Any, path: str = "root") -> list[tuple[str, str, int]]:
    """
    Temukan semua field numerik yang namanya cocok dengan _COUNT_FIELD_RE.
    Kembalikan list of (field_path, field_name, value).
    """
    results: list[tuple[str, str, int]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            field_path = f"{path}.{k}"
            if isinstance(v, int) and not isinstance(v, bool):
                if _COUNT_FIELD_RE.search(k):
                    results.append((field_path, k, v))
                else:
                    results.extend(_find_numeric_fields(v, field_path))
            elif isinstance(v, (dict, list)):
                results.extend(_find_numeric_fields(v, field_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            results.extend(_find_numeric_fields(item, f"{path}[{i}]"))
    return results


def _find_error_flags(data: Any, path: str = "root") -> list[tuple[str, str, Any]]:
    """
    Deteksi field yang mengindikasikan kondisi error — boolean DAN string.
    Boolean: field bernama *_exceeded, *_error, dll bernilai True
    String : field bernilai string yang cocok dengan pola kondisi error
    """
    results: list[tuple[str, str, Any]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            field_path = f"{path}.{k}"
            # Boolean True dengan nama error
            if isinstance(v, bool) and v is True:
                if _ERROR_FLAG_RE.search(k):
                    results.append((field_path, k, v))
            # String yang nilainya adalah kode error
            elif isinstance(v, str) and _ERROR_STRING_PATTERN.match(v.strip()):
                results.append((field_path, k, v))
            elif isinstance(v, (dict, list)):
                results.extend(_find_error_flags(v, field_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            results.extend(_find_error_flags(item, f"{path}[{i}]"))
    return results


# ── Entry point ───────────────────────────────────────────────────────────────

def analyze_consistency(data: Any) -> list[CheckResult]:
    """
    Entry point utama. Dipanggil dari cli.py setelah file di-parse.
    Menerima data yang sudah di-parse (dict/list), bukan raw string.

    Jika data None atau string (parse gagal), langsung return [] — silent skip.
    """
    if data is None or isinstance(data, str):
        return []

    checks: list[CheckResult] = []

    # ── Pemeriksaan 1: Count-Content Mismatch ─────────────────────────────
    # Bandingkan setiap field numerik yang terlihat seperti "jumlah"
    # dengan panjang aktual array terdekat di dalam struktur yang sama.
    numeric_fields = _find_numeric_fields(data)
    arrays         = _find_arrays(data)

    for field_path, field_name, declared_count in numeric_fields:
        if declared_count <= 0:
            continue

        # Cari array yang path-nya paling dekat dengan field ini
        field_parent = ".".join(field_path.split(".")[:-1])
        closest_array: tuple[str, list] | None = None
        closest_distance = float("inf")

        for arr_path, arr_data in arrays:
            arr_parent = ".".join(arr_path.split(".")[:-1])
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

        if mismatch_ratio >= 0.90:
            # Mismatch ekstrem: deklarasi 1847 tapi isi 72 (FAA scenario)
            checks.append(CheckResult(
                check="metadata_count_mismatch_critical",
                score=2,
                detail=(
                    f"Inkonsistensi kritis: field '{field_name}' "
                    f"mendeklarasikan {declared_count} item, "
                    f"tapi array '{arr_path}' hanya berisi "
                    f"{actual_count} item "
                    f"({mismatch_ratio:.0%} mismatch). "
                    f"Kemungkinan truncation atau partial overwrite."
                ),
                value={
                    "declared":       declared_count,
                    "actual":         actual_count,
                    "mismatch_ratio": round(mismatch_ratio, 3),
                },
                remediation=(
                    "Verifikasi integritas file. Kemungkinan file ini "
                    "di-replace dengan versi yang lebih lama atau tidak lengkap."
                ),
            ))
        elif mismatch_ratio >= 0.50:
            checks.append(CheckResult(
                check="metadata_count_mismatch_warn",
                score=1,
                detail=(
                    f"Field '{field_name}' mendeklarasikan {declared_count} item "
                    f"tapi array aktual berisi {actual_count} item "
                    f"({mismatch_ratio:.0%} mismatch)."
                ),
                value={
                    "declared":       declared_count,
                    "actual":         actual_count,
                    "mismatch_ratio": round(mismatch_ratio, 3),
                },
                remediation="Periksa konsistensi antara metadata dan konten file.",
            ))

    # ── Pemeriksaan 2: Hard Limit Exceeded ────────────────────────────────
    # Cari pasangan field (limit/max/capacity) vs field count yang melebihinya.
    # Hanya berlaku di level root dict untuk menghindari false positive nested.
    if isinstance(data, dict):
        limit_fields = {
            k: v for k, v in data.items()
            if isinstance(v, int) and not isinstance(v, bool)
            and _LIMIT_FIELD_RE.search(k)
        }
        count_fields = {
            k: v for k, v in data.items()
            if isinstance(v, int) and not isinstance(v, bool)
            and _COUNT_FIELD_RE.search(k)
        }
        for lk, lv in limit_fields.items():
            for ck, cv in count_fields.items():
                if lv > 0:
                    if cv > lv:
                        excess_ratio = (cv - lv) / lv
                        score = 2 if excess_ratio >= 0.10 else 1
                        checks.append(CheckResult(
                            check="hard_limit_exceeded",
                            score=score,
                            detail=(
                                f"Field '{ck}' bernilai {cv} "
                                f"melebihi limit yang dideklarasikan "
                                f"'{lk}': {lv} "
                                f"(+{excess_ratio:.0%} di atas batas)."
                            ),
                            value={
                                "count_field": ck, "count_value": cv,
                                "limit_field": lk, "limit_value": lv,
                            },
                            remediation=(
                                "File ini melebihi batas yang dikonfigurasi. "
                                "Propagasi file ini kemungkinan menyebabkan error downstream."
                            ),
                        ))
                    else:
                        proximity = cv / lv
                        if 0.5 <= proximity <= 1.0:   # 50-100% dari limit
                            checks.append(CheckResult(
                                check="approaching_hard_limit",
                                score=1,   # WARN saja, bukan CRITICAL
                                detail=(
                                    f"Field '{ck}' bernilai {cv}, mencapai "
                                    f"{proximity:.0%} dari limit '{lk}': {lv}. "
                                    f"Pantau pertumbuhan lebih lanjut."
                                ),
                                value={"proximity_ratio": round(proximity, 3)},
                                remediation="File mendekati batas kapasitas yang dikonfigurasi.",
                            ))

    # ── Pemeriksaan 3: Error State Boolean Flag ───────────────────────────
    # Field boolean dengan nama error/warning yang bernilai True adalah sinyal
    # bahwa sistem yang menggenerate file ini sudah tahu ada masalah.
    error_flags = _find_error_flags(data)
    if error_flags:
        flag_summary = ", ".join(f"'{name}'=True" for _, name, _ in error_flags[:5])
        if len(error_flags) > 5:
            flag_summary += f" (+{len(error_flags) - 5} lainnya)"
        score = 2 if len(error_flags) >= 2 else 1
        checks.append(CheckResult(
            check="error_state_flags_active",
            score=score,
            detail=(
                f"Ditemukan {len(error_flags)} field error/warning "
                f"aktif (True) di dalam file: {flag_summary}. "
                f"File ini mungkin di-generate saat sistem sedang dalam "
                f"kondisi degraded."
            ),
            value={"active_flags": [name for _, name, _ in error_flags]},
            remediation=(
                "Periksa apakah file ini di-generate saat sistem "
                "mengalami gangguan. File konfigurasi dari kondisi error "
                "tidak seharusnya dipropagasikan."
            ),
        ))

    return checks
