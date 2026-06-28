"""
src/csg/git_tracker.py — Stateless Git Tracker
"""
import subprocess
import logging
from typing import Dict

logger = logging.getLogger(__name__)

def get_renamed_files() -> Dict[str, str]:
    """
    Mendeteksi file yang di-rename (diubah namanya) di Git agar tetap cocok dengan baseline lama.
    Mengembalikan dictionary: {new_path: old_path}
    """
    rename_map = {}
    try:
        # Menjalankan perintah git diff untuk mencari status 'R' (Renamed)
        cmd = ["git", "diff", "--name-status", "HEAD~1", "HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        for line in result.stdout.strip().split('\n'):
            parts = line.split('\t')
            if parts and parts[0].startswith('R'):
                # Format: R100 \t old_path \t new_path
                if len(parts) >= 3:
                    rename_map[parts[2]] = parts[1]
    except Exception:
        # Jika bukan repositori git atau tidak ada commit sebelumnya, abaikan
        pass
        
    return rename_map

def get_previous_size_from_git(filepath: str, ref: str = "HEAD~1") -> int | None:
    """
    [STATELESS FALLBACK]
    Bertanya langsung kepada Git tentang ukuran file di commit sebelumnya.
    Sangat ampuh di CI/CD ketika file .csg-baseline.json tidak tersedia (Cold Start).
    """
    try:
        # Git internal selalu menggunakan forward slash
        git_path = filepath.replace('\\', '/')
        
        # Perintah 'git cat-file -s' mengembalikan ukuran asli blob/file di histori git
        cmd = ["git", "cat-file", "-s", f"{ref}:{git_path}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return int(result.stdout.strip())
    except Exception:
        # Akan gagal jika file tersebut adalah file yang benar-benar baru di commit ini
        return None