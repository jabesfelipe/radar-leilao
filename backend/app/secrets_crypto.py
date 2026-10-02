"""Criptografia reversível de credenciais de portal (TASK 75.1).

A credencial de um ``PortalAccess`` precisa ser recuperável para uso explícito, então
hash irreversível NÃO serve. Usamos Fernet (AES-128-CBC + HMAC) da biblioteca
``cryptography``, com a chave vinda de ambiente (``PORTAL_SECRET_KEY``) — NUNCA do
banco nem versionada. Falha-fechada: sem chave válida, o sistema recusa armazenar ou
revelar credenciais (em vez de guardar texto puro).

O valor persistido em ``portal_accesses.secret`` é o token Fernet (texto cifrado,
prefixado por ``enc:v1:``), não a senha. Nenhum log imprime o valor.
"""
from __future__ import annotations

import base64
import hashlib

from .config import settings

_PREFIX = "enc:v1:"


class SecretKeyNotConfigured(RuntimeError):
    """A chave de criptografia de credenciais não está configurada no ambiente."""


def _fernet():
    try:
        from cryptography.fernet import Fernet
    except Exception as exc:  # pragma: no cover - dependência obrigatória em runtime
        raise SecretKeyNotConfigured("Biblioteca de criptografia indisponível.") from exc
    raw = settings.portal_secret_key
    if not raw:
        raise SecretKeyNotConfigured(
            "PORTAL_SECRET_KEY não configurada: o armazenamento de credenciais está desabilitado."
        )
    # Aceita tanto uma chave Fernet pronta (urlsafe base64 de 32 bytes) quanto uma
    # passphrase arbitrária (derivada por SHA-256 para 32 bytes). Determinístico.
    key_bytes = raw.encode("utf-8")
    try:
        if len(base64.urlsafe_b64decode(key_bytes)) == 32:
            return Fernet(key_bytes)
    except Exception:
        pass
    derived = base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())
    return Fernet(derived)


def is_configured() -> bool:
    try:
        _fernet()
        return True
    except SecretKeyNotConfigured:
        return False


def encrypt_secret(plaintext: str | None) -> str | None:
    """Cifra a credencial para persistência. ``None``/vazio → None (sem credencial)."""
    if plaintext is None or plaintext == "":
        return None
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt_secret(stored: str | None) -> str | None:
    """Recupera a credencial em claro a partir do valor cifrado armazenado."""
    if stored is None or stored == "":
        return None
    if not stored.startswith(_PREFIX):
        # Valor não cifrado (não deveria ocorrer após 75.1). Não vaza em claro:
        # retorna None e deixa o chamador tratar como indisponível.
        return None
    token = stored[len(_PREFIX):].encode("ascii")
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except Exception:
        return None


def has_secret(stored: str | None) -> bool:
    return bool(stored)
