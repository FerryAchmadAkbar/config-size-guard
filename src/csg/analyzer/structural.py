"""
analyzer/structural.py — Optional Structural Scanner
"""
from pathlib import Path
import json
from ..models import CheckResult

import re

_JSONC_COMMENT_PATTERN = re.compile(
    r'^\s*(//.*|/\*.*?\*/)', re.MULTILINE | re.DOTALL
)

def _is_jsonc(content: str) -> bool:
    """
    Deteksi apakah file JSON menggunakan JSONC syntax (komentar //).
    Jika ya, strict-format validation harus di-skip karena JSONC
    adalah format legitimate yang digunakan di VS Code, tsconfig.json, dll.
    """
    # Sample 50 baris pertama untuk efisiensi
    sample = "\n".join(content.splitlines()[:50])
    return bool(_JSONC_COMMENT_PATTERN.search(sample))

def analyze_structural(filepath: Path, baseline_entry: dict | None, cfg: dict) -> list[CheckResult]:
    checks = []
    ext = filepath.suffix.lower()
    
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return checks

    if ext == '.json' and _is_jsonc(content):
        return [CheckResult(
            check="jsonc_format_detected",
            score=0,  # PASS — ini informasi, bukan anomali
            detail=(
                f"File menggunakan JSONC syntax (komentar // terdeteksi). "
                f"Strict-format JSON validation dilewati untuk format ini."
            ),
            value={"format": "jsonc"},
        )]

    # Pengecekan dasar yang memicu CRITICAL jika format rusak (indikasi Obfuscation)
    if ext == '.json':
        try:
            json.loads(content)
        except json.JSONDecodeError:
            checks.append(CheckResult(
                check="malformed_json_structure", score=2,
                detail="Format JSON rusak. Kemungkinan Obfuscation / Payload Injeksi."
            ))
            
    # Format lain ditiadakan untuk menjaga CSG tetap ringan tanpa dependensi eksternal
    return checks