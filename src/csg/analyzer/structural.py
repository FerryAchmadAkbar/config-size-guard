from pathlib import Path
import json
from ..models import CheckResult
import re
_JSONC_COMMENT_PATTERN = re.compile('^\\s*(//.*|/\\*.*?\\*/)', re.MULTILINE | re.DOTALL)

def _is_jsonc(content: str) -> bool:
    sample = '\n'.join(content.splitlines()[:50])
    return bool(_JSONC_COMMENT_PATTERN.search(sample))

def analyze_structural(filepath: Path, baseline_entry: dict | None, cfg: dict) -> list[CheckResult]:
    checks = []
    ext = filepath.suffix.lower()
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return checks
    if ext == '.json' and _is_jsonc(content):
        return [CheckResult(check='jsonc_format_detected', score=0, detail=f'File menggunakan JSONC syntax (komentar // terdeteksi). Strict-format JSON validation dilewati untuk format ini.', value={'format': 'jsonc'})]
    if ext == '.json':
        try:
            json.loads(content)
        except json.JSONDecodeError:
            checks.append(CheckResult(check='malformed_json_structure', score=2, detail='Format JSON rusak. Kemungkinan Obfuscation / Payload Injeksi.'))
    return checks