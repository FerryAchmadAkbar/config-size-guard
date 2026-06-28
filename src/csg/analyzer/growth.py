"""
analyzer/growth.py — Relative Growth & Shrinkage Scanner
Mendeteksi dua arah anomali ukuran:
  - Pembengkakan (growth)  : S1 Cloudflare, S2 CrowdStrike, S3 Roblox
  - Penyusutan (shrinkage) : S4 FAA truncation — Format-Aware Baseline:
  - Gunakan normalized_size (CRLF→LF) untuk perbandingan yang akurat di Windows
  - Skip comparison jika format file berubah (misal TOML→YAML setelah re-parse)
    untuk mencegah false positive akibat konversi format
"""
from pathlib import Path

from ..baseline import get_normalized_size
from ..models import CheckResult


def analyze_growth(
    current_size: int,
    base_entry: dict | None,
    cfg: dict,
    filepath: Path | None = None,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not base_entry:
        return results

    # ── Pilih ukuran baseline yang paling akurat ───────────────────────────
    # Prioritas: normalized_size (CRLF-safe) → size_bytes → size (format lama)
    prev_size = (
        base_entry.get("normalized_size")
        or base_entry.get("size_bytes")
        or base_entry.get("size", 0)
    )
    if not prev_size or prev_size == 0:
        return results

    # ── Format-change guard ────────────────────────────────────────────────
    # Jika format file berubah (misal .toml di-parse ulang jadi .yaml),
    # growth ratio tidak reliable — skip dan beri sinyal WARN ringan.
    if filepath is not None:
        original_fmt = base_entry.get("original_format", "")
        current_fmt  = filepath.suffix.lower()
        if original_fmt and original_fmt != current_fmt:
            results.append(CheckResult(
                check="format_changed",
                score=1,
                detail=(
                    f"Format file berubah dari '{original_fmt}' ke '{current_fmt}'. "
                    f"Growth ratio tidak dihitung untuk mencegah false positive."
                ),
                value={"from": original_fmt, "to": current_fmt},
                remediation="Verifikasi apakah perubahan format file ini disengaja.",
            ))
            return results

    # ── Gunakan normalized_size untuk current jika filepath tersedia ───────
    if filepath is not None:
        try:
            current_size = get_normalized_size(filepath)
        except Exception:
            pass  # fallback ke current_size yang dikirim caller

    growth_cfg = cfg.get("growth", {})

    # ── Threshold pembengkakan ─────────────────────────────────────────────
    g_crit = float(growth_cfg.get("drift_critical_percent", 80.0))
    g_warn = float(growth_cfg.get("drift_warn_percent",     40.0))

    # ── Threshold penyusutan (FAA Guard) ──────────────────────────────────
    s_crit = float(growth_cfg.get("shrinkage_critical_percent", 70.0))
    s_warn = float(growth_cfg.get("shrinkage_warn_percent",     30.0))

    current_kb  = current_size / 1024
    baseline_kb = prev_size    / 1024

    if current_size > prev_size:
        # ── Pembengkakan ──────────────────────────────────────────────────
        growth_pct = ((current_size / prev_size) - 1) * 100
        if growth_pct >= g_crit:
            results.append(CheckResult(
                check="growth_drift_critical",
                score=2,
                detail=(
                    f"File membengkak {growth_pct:.1f}% dari baseline "
                    f"({baseline_kb:.1f} KB → {current_kb:.1f} KB). "
                    f"Kemungkinan array explosion atau config dump."
                ),
                value=current_size,
                remediation="Periksa apakah ada loop tak terbatas atau data dump yang tidak disengaja.",
                is_delta=True,
            ))
        elif growth_pct >= g_warn:
            results.append(CheckResult(
                check="growth_drift_warn",
                score=1,
                detail=(
                    f"File membengkak {growth_pct:.1f}% dari baseline "
                    f"({baseline_kb:.1f} KB → {current_kb:.1f} KB)."
                ),
                value=current_size,
                remediation="Verifikasi apakah pertumbuhan ukuran ini disengaja.",
                is_delta=True,
            ))

    elif current_size < prev_size:
        # ── Penyusutan (FAA Guard) ────────────────────────────────────────
        shrink_pct = (1 - (current_size / prev_size)) * 100
        if shrink_pct >= s_crit:
            results.append(CheckResult(
                check="shrinkage_drift_critical",
                score=2,
                detail=(
                    f"File menyusut {shrink_pct:.1f}% dari baseline "
                    f"({baseline_kb:.1f} KB → {current_kb:.1f} KB). "
                    f"Kemungkinan truncation, partial overwrite, atau file "
                    f"diganti dengan versi backup yang lebih lama."
                ),
                value=current_size,
                remediation="Verifikasi apakah perubahan ukuran ini disengaja.",
                is_delta=True,
            ))
        elif shrink_pct >= s_warn:
            results.append(CheckResult(
                check="shrinkage_drift_warn",
                score=1,
                detail=(
                    f"File menyusut {shrink_pct:.1f}% dari baseline "
                    f"({baseline_kb:.1f} KB → {current_kb:.1f} KB)."
                ),
                value=current_size,
                remediation="Periksa apakah penyusutan ukuran ini wajar.",
                is_delta=True,
            ))

    return results
