import yaml
from pathlib import Path

def load_config(config_path: str='csg.config.yaml') -> dict:
    path = Path(config_path)
    if not path.exists():
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f'[WARN] Gagal membaca konfigurasi {config_path}: {e}')
        return {}

def get_threshold_for_file(filepath: str, cfg: dict) -> dict:
    return cfg