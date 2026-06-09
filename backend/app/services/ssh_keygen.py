from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.services.ssh_client import get_key_fingerprint


def generate_ssh_keypair(comment: str = "opsdeck@generated") -> dict[str, str]:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_openssh = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ).decode()

    public_line = f"{public_openssh} {comment}"

    return {
        "public_key": public_line,
        "private_key": private_pem,
        "fingerprint": get_key_fingerprint(private_pem),
        "instructions": (
            "Add the public key to the target server's ~/.ssh/authorized_keys, "
            "then save the private key below in OpsDeck Settings."
        ),
    }
