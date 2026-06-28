import subprocess
import logging
from typing import Dict
logger = logging.getLogger(__name__)

def get_renamed_files() -> Dict[str, str]:
    rename_map = {}
    try:
        cmd = ['git', 'diff', '--name-status', 'HEAD~1', 'HEAD']
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for line in result.stdout.strip().split('\n'):
            parts = line.split('\t')
            if parts and parts[0].startswith('R'):
                if len(parts) >= 3:
                    rename_map[parts[2]] = parts[1]
    except Exception:
        pass
    return rename_map

def get_previous_size_from_git(filepath: str, ref: str='HEAD~1') -> int | None:
    try:
        git_path = filepath.replace('\\', '/')
        cmd = ['git', 'cat-file', '-s', f'{ref}:{git_path}']
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(result.stdout.strip())
    except Exception:
        return None