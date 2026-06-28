import re
from typing import NamedTuple

class SafePattern(NamedTuple):
    name: str
    pattern: re.Pattern
    category: str
    note: str
_RAW: list[tuple[str, str, str, str]] = [('pem_begin', '-----BEGIN [A-Z ]{1,30}-----', 'crypto', 'PEM header'), ('pem_end', '-----END [A-Z ]{1,30}-----', 'crypto', 'PEM footer'), ('sha256_digest', 'sha256:[a-f0-9]{64}', 'crypto', 'SHA256 hash'), ('sha512_digest', 'sha512:[a-f0-9]{128}', 'crypto', 'SHA512 hash'), ('sha1_digest', 'sha1:[a-f0-9]{40}', 'crypto', 'SHA1 hash'), ('bcrypt_hash', '\\$2[aby]\\$\\d{2}\\$[./A-Za-z0-9]{53}', 'crypto', 'Bcrypt password hash'), ('docker_image_digest', 'sha256:[a-f0-9]{64}', 'container', 'Docker image digest'), ('uuid_any', '[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}', 'id', 'UUID / Any'), ('git_sha', '\\b[0-9a-f]{40}\\b', 'id', 'Git commit SHA'), ('hex_id_short', '\\b[0-9a-f]{32}\\b', 'id', 'MD5 hash/hex ID'), ('jwt_token', 'eyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}', 'auth', 'JWT token'), ('https_url', 'https?://[a-zA-Z0-9._\\-/:%?=&#+@]{15,}', 'network', 'HTTP/HTTPS URL'), ('ssh_key', 'AAAA[A-Za-z0-9+/]{20,}', 'crypto', 'SSH Public Key'), ('pgp_block', 'mQENB[A-Za-z0-9+/]+', 'crypto', 'PGP Block')]
SAFE_REGEXES = [re.compile(p[1]) for p in _RAW]

def is_safe_token(token: str) -> bool:
    return any((regex.search(token) for regex in SAFE_REGEXES))