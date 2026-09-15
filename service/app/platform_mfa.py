from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6
TOTP_ISSUER = "Mago Bot"


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    normalized = "".join(secret.upper().split())
    return base64.b32decode(normalized + "=" * (-len(normalized) % 8), casefold=True)


def totp_at(secret: str, timestamp: int | None = None, step: int = TOTP_STEP_SECONDS) -> tuple[str, int]:
    now = int(time.time() if timestamp is None else timestamp)
    counter = now // step
    digest = hmac.new(_decode_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**TOTP_DIGITS)).zfill(TOTP_DIGITS), counter


def verify_totp(secret: str, code: str, timestamp: int | None = None, skew: int = 1) -> tuple[bool, int | None]:
    normalized = "".join(str(code).split())
    if len(normalized) != TOTP_DIGITS or not normalized.isdigit():
        return False, None
    now = int(time.time() if timestamp is None else timestamp)
    current_counter = now // TOTP_STEP_SECONDS
    for counter in range(current_counter - skew, current_counter + skew + 1):
        expected, _ = totp_at(secret, counter * TOTP_STEP_SECONDS)
        if hmac.compare_digest(expected, normalized):
            return True, counter
    return False, None


def otpauth_uri(secret: str, account: str, issuer: str = TOTP_ISSUER) -> str:
    label = f"{issuer}:{account}"
    return "otpauth://totp/" + quote(label) + "?secret=" + quote(secret) + "&issuer=" + quote(issuer) + "&algorithm=SHA1&digits=6&period=30"


def generate_recovery_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(5).upper() for _ in range(count)]


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(("mago-recovery:" + code.strip().upper()).encode("utf-8")).hexdigest()


def hash_recovery_codes(codes: list[str]) -> list[str]:
    return [hash_recovery_code(code) for code in codes]


def consume_recovery_code(code: str, hashes: list[str]) -> tuple[bool, list[str]]:
    candidate = hash_recovery_code(code)
    for index, stored in enumerate(hashes):
        if hmac.compare_digest(candidate, stored):
            return True, hashes[:index] + hashes[index + 1 :]
    return False, hashes
