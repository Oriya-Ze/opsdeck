from sqlalchemy.orm import Session

from app.models.ssh_settings import SshSettings
from app.services.encryption import decrypt_value, encrypt_value
from app.services.ssh_client import get_key_fingerprint


def get_ssh_settings(db: Session) -> SshSettings | None:
    return db.query(SshSettings).filter(SshSettings.id == 1).first()


def is_ssh_configured(db: Session) -> bool:
    return get_ssh_settings(db) is not None


def get_decrypted_private_key(db: Session) -> tuple[str, str] | None:
    """Return (ssh_user, private_key) or None if not configured."""
    settings = get_ssh_settings(db)
    if not settings:
        return None
    return settings.ssh_user, decrypt_value(settings.encrypted_private_key)


def save_ssh_settings(
    db: Session,
    ssh_user: str,
    private_key: str | None = None,
    public_key: str | None = None,
    passphrase: str | None = None,
) -> SshSettings:
    existing = get_ssh_settings(db)

    if existing:
        existing.ssh_user = ssh_user
        if private_key:
            existing.encrypted_private_key = encrypt_value(private_key.strip())
            existing.key_fingerprint = get_key_fingerprint(private_key, passphrase)
        if public_key is not None:
            existing.public_key = public_key
        db.commit()
        db.refresh(existing)
        return existing

    if not private_key:
        raise ValueError("Private key is required for initial SSH setup")

    fingerprint = get_key_fingerprint(private_key, passphrase)
    encrypted = encrypt_value(private_key.strip())

    row = SshSettings(
        id=1,
        ssh_user=ssh_user,
        encrypted_private_key=encrypted,
        key_fingerprint=fingerprint,
        public_key=public_key,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_ssh_settings(db: Session) -> bool:
    settings = get_ssh_settings(db)
    if not settings:
        return False
    db.delete(settings)
    db.commit()
    return True
