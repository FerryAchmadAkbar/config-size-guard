"""
src/csg/safe_patterns.py — Global Pattern Veto Library
"""
import re
from typing import NamedTuple

class SafePattern(NamedTuple):
    name: str
    pattern: re.Pattern
    category: str
    note: str

_RAW: list[tuple[str, str, str, str]] = [
    ("pem_begin", r"-----BEGIN [A-Z ]{1,30}-----", "crypto", "PEM header"),
    ("pem_end", r"-----END [A-Z ]{1,30}-----", "crypto", "PEM footer"),
    ("sha256_digest", r"sha256:[a-f0-9]{64}", "crypto", "SHA256 hash"),
    ("sha512_digest", r"sha512:[a-f0-9]{128}", "crypto", "SHA512 hash"),
    ("sha1_digest", r"sha1:[a-f0-9]{40}", "crypto", "SHA1 hash"),
    ("bcrypt_hash", r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}", "crypto", "Bcrypt password hash"),
    ("docker_image_digest", r"sha256:[a-f0-9]{64}", "container", "Docker image digest"),
    ("uuid_any", r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", "id", "UUID / Any"),
    ("git_sha", r"\b[0-9a-f]{40}\b", "id", "Git commit SHA"),
    ("hex_id_short", r"\b[0-9a-f]{32}\b", "id", "MD5 hash/hex ID"),
    ("jwt_token", r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "auth", "JWT token"),
    ("https_url", r"https?://[a-zA-Z0-9._\-/:%?=&#+@]{15,}", "network", "HTTP/HTTPS URL"),
    ("ssh_key", r"AAAA[A-Za-z0-9+/]{20,}", "crypto", "SSH Public Key"),
    ("pgp_block", r"mQENB[A-Za-z0-9+/]+", "crypto", "PGP Block")
]

# Compile sekali untuk efisiensi CPU
SAFE_REGEXES = [re.compile(p[1]) for p in _RAW]

def is_safe_token(token: str) -> bool:
    """Mengembalikan True jika token cocok dengan whitelist pola konfigurasi wajar."""
    return any(regex.search(token) for regex in SAFE_REGEXES)