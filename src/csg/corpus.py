"""
src/csg/corpus.py — Layer 3: statistik historis dari file PASS (corpus learning)
"""
import json
import statistics
from pathlib import Path

_CORPUS_MAX_PER_EXT = 200

def _iqr_stats(values: list[int]) -> dict:
    if len(values) < 4:
        med = statistics.median(values) if values else 0
        return {"median": med, "iqr": 0.0, "q3": med, "sample_size": len(values)}
    q1, _, q3 = statistics.quantiles(values, n=4)
    return {
        "median": statistics.median(values),
        "iqr": q3 - q1,
        "q3": q3,
        "sample_size": len(values),
    }


class CorpusStats:
    """Distribusi ukuran file bersih per ekstensi, diakumulasi dari scan PASS."""

    def __init__(self, path: str | Path = ".csg-corpus.json"):
        self.path = Path(path)
        self._sizes_by_ext: dict[str, list[int]] = self._load()

    def _load(self) -> dict[str, list[int]]:
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {k: list(v) for k, v in raw.get("sizes_by_ext", {}).items()}
        except (OSError, json.JSONDecodeError, TypeError):
            return {}

    def get_ext_stats(self, ext: str) -> dict | None:
        sizes = self._sizes_by_ext.get(ext.lower() or ".unknown", [])
        if len(sizes) < 4:
            return None
        return _iqr_stats(sorted(sizes))

    def update_from_scan(self, passed_files: list[Path]) -> int:
        updated = 0
        for filepath in passed_files:
            try:
                size = filepath.stat().st_size
            except OSError:
                continue
            ext = filepath.suffix.lower() or ".unknown"
            bucket = self._sizes_by_ext.setdefault(ext, [])
            bucket.append(size)
            if len(bucket) > _CORPUS_MAX_PER_EXT:
                del bucket[: len(bucket) - _CORPUS_MAX_PER_EXT]
            updated += 1
        return updated

    def save(self) -> None:
        payload = {"sizes_by_ext": self._sizes_by_ext}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
