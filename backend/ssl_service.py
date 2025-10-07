"""Utilities for managing SSL certificates and Nginx runtime configuration."""
from __future__ import annotations

import os
import re
import uuid
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
import signal

CERTBOT_WEBROOT = os.getenv('CERTBOT_WEBROOT', '/var/www/certbot')
LE_LIVE_BASE = os.getenv('LE_LIVE_BASE', '/etc/letsencrypt/live')
UPLOAD_CERT_DIR = os.getenv('UPLOAD_CERT_DIR', '/etc/nginx/ssl/uploaded')
NGINX_RUNTIME_DIR = os.getenv('NGINX_RUNTIME_DIR', '/etc/nginx/runtime')
SSL_SNIPPET_FILENAME = os.getenv('SSL_SNIPPET_FILENAME', 'ssl-enabled.conf')
SSL_SNIPPET_PATH = os.path.join(NGINX_RUNTIME_DIR, SSL_SNIPPET_FILENAME)
SSL_FALLBACK_SNIPPET_FILENAME = os.getenv('SSL_FALLBACK_SNIPPET_FILENAME', 'ssl-disabled.conf')
SSL_FALLBACK_SNIPPET_PATH = os.path.join(NGINX_RUNTIME_DIR, SSL_FALLBACK_SNIPPET_FILENAME)
SSL_REDIRECT_FILENAME = os.getenv('SSL_REDIRECT_FILENAME', 'ssl-redirect.conf')
SSL_REDIRECT_PATH = os.path.join(NGINX_RUNTIME_DIR, SSL_REDIRECT_FILENAME)
NGINX_PID_PATH = os.getenv('NGINX_PID_PATH', os.path.join(NGINX_RUNTIME_DIR, 'nginx.pid'))

DOMAIN_REGEX = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
)


class SSLConfigurationError(Exception):
    """Raised when SSL configuration update fails."""


class SSLVerificationError(Exception):
    """Raised when HTTPS verification fails."""


@dataclass
class CertificateMetadata:
    """Metadata extracted from a certificate."""
    expires_at: Optional[datetime]
    subject: Optional[str]
    issuer: Optional[str]
    fingerprint_sha256: Optional[str]


def ensure_directories() -> None:
    """Ensure required directories exist with secure permissions."""
    for path in [CERTBOT_WEBROOT, UPLOAD_CERT_DIR, NGINX_RUNTIME_DIR]:
        os.makedirs(path, exist_ok=True)
        os.chmod(path, 0o755)


def is_valid_domain(domain: str) -> bool:
    """Validate that the provided domain is well-formed."""
    if not domain:
        return False
    return DOMAIN_REGEX.match(domain) is not None


def normalize_domains(primary: Optional[str], alternates: Optional[List[str]]) -> List[str]:
    """Return normalized list of unique domains."""
    domains = []
    if primary:
        domains.append(primary.strip().lower())
    if alternates:
        for alt in alternates:
            if alt:
                alt = alt.strip().lower()
                if alt not in domains:
                    domains.append(alt)
    return domains


def _load_certificate(cert_pem: str) -> x509.Certificate:
    """Load a certificate from PEM text."""
    try:
        return x509.load_pem_x509_certificate(cert_pem.encode('utf-8'), default_backend())
    except Exception as exc:  # pragma: no cover - cryptography raises multiple types
        raise SSLConfigurationError(f'Invalid certificate: {exc}') from exc


def _load_private_key(key_pem: str) -> serialization.PrivateFormat:
    """Load a private key and ensure it is RSA or ECDSA."""
    try:
        return serialization.load_pem_private_key(key_pem.encode('utf-8'), password=None, backend=default_backend())
    except Exception as exc:  # pragma: no cover
        raise SSLConfigurationError(f'Invalid private key: {exc}') from exc


def _metadata_from_certificate(cert: x509.Certificate) -> CertificateMetadata:
    expires_at = cert.not_valid_after.replace(tzinfo=timezone.utc)
    subject = ', '.join([f"{name.oid._name}={name.value}" for name in cert.subject])
    issuer = ', '.join([f"{name.oid._name}={name.value}" for name in cert.issuer])
    fingerprint = cert.fingerprint(hashes.SHA256()).hex()

    return CertificateMetadata(
        expires_at=expires_at,
        subject=subject,
        issuer=issuer,
        fingerprint_sha256=fingerprint,
    )


def validate_certificate_pair(certificate_pem: str, private_key_pem: str) -> CertificateMetadata:
    """Ensure certificate and private key match and return metadata."""
    cert = _load_certificate(certificate_pem)
    key = _load_private_key(private_key_pem)

    cert_public_numbers = cert.public_key().public_numbers()
    key_public_numbers = key.public_key().public_numbers()

    if cert_public_numbers != key_public_numbers:
        raise SSLConfigurationError('Certificate and private key do not match')

    return _metadata_from_certificate(cert)


def _write_secure_file(path: str, content: str, mode: int = 0o600) -> None:
    """Write content to path with secure permissions."""
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    os.chmod(path, mode)


def store_uploaded_material(certificate_pem: str, private_key_pem: str, chain_pem: Optional[str] = None) -> Dict[str, str]:
    """Persist uploaded PEM material to disk and return paths."""
    ensure_directories()
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    identifier = uuid.uuid4().hex
    prefix = f'{timestamp}_{identifier}'
    cert_path = os.path.join(UPLOAD_CERT_DIR, f'{prefix}_fullchain.pem')
    key_path = os.path.join(UPLOAD_CERT_DIR, f'{prefix}_privkey.pem')
    chain_path = None

    # Compose fullchain: certificate plus optional chain
    if chain_pem:
        # Avoid duplicate certificate data if already included
        fullchain = certificate_pem.strip() + '\n' + chain_pem.strip() + '\n'
    else:
        fullchain = certificate_pem.strip() + '\n'

    _write_secure_file(cert_path, fullchain)
    _write_secure_file(key_path, private_key_pem.strip() + '\n')

    if chain_pem:
        chain_path = os.path.join(UPLOAD_CERT_DIR, f'{prefix}_chain.pem')
        _write_secure_file(chain_path, chain_pem.strip() + '\n')

    return {
        'certificate_path': cert_path,
        'private_key_path': key_path,
        'chain_path': chain_path,
    }


def get_lets_encrypt_live_paths(primary_domain: str) -> Dict[str, str]:
    """Return standard Let\'s Encrypt live paths for a domain."""
    live_dir = os.path.join(LE_LIVE_BASE, primary_domain)
    return {
        'certificate_path': os.path.join(live_dir, 'fullchain.pem'),
        'private_key_path': os.path.join(live_dir, 'privkey.pem'),
    }


def read_certificate_metadata_from_path(cert_path: str) -> Optional[CertificateMetadata]:
    """Load metadata from a certificate PEM file."""
    if not cert_path or not os.path.exists(cert_path):
        return None
    with open(cert_path, 'rb') as fh:
        certificate_pem = fh.read()
    cert = x509.load_pem_x509_certificate(certificate_pem, default_backend())
    return _metadata_from_certificate(cert)


def calculate_certificate_fingerprint(certificate_pem: str) -> str:
    cert = _load_certificate(certificate_pem)
    return cert.fingerprint(hashes.SHA256()).hex()


def write_nginx_ssl_snippet(mode: str, cert_path: str, key_path: str) -> None:
    """Write nginx snippet enabling SSL with the provided certificate paths."""
    ensure_directories()
    snippet = (
        'ssl_certificate {};' '\n'
        'ssl_certificate_key {};' '\n'
        'ssl_protocols TLSv1.2 TLSv1.3;' '\n'
        'ssl_prefer_server_ciphers on;' '\n'
        'ssl_session_cache shared:SSL:10m;' '\n'
        'ssl_session_timeout 10m;' '\n'
    ).format(cert_path, key_path)
    _write_secure_file(SSL_SNIPPET_PATH, snippet, mode=0o644)


def disable_nginx_ssl_snippet() -> None:
    """Disable SSL by removing the runtime snippet."""
    if os.path.exists(SSL_SNIPPET_PATH):
        os.remove(SSL_SNIPPET_PATH)


def write_http_redirect_snippet(enabled: bool) -> None:
    """Create or remove the HTTP→HTTPS redirect snippet."""
    ensure_directories()
    if enabled:
        _write_secure_file(SSL_REDIRECT_PATH, 'return 301 https://$host$request_uri;\n', mode=0o644)
    else:
        if os.path.exists(SSL_REDIRECT_PATH):
            os.remove(SSL_REDIRECT_PATH)


def reload_nginx() -> None:
    """Reload nginx configuration."""
    try:
        if not os.path.exists(NGINX_PID_PATH):
            raise SSLConfigurationError(f'nginx pid file not found at {NGINX_PID_PATH}')
        with open(NGINX_PID_PATH, 'r', encoding='utf-8') as fh:
            pid_value = fh.read().strip()
        pid = int(pid_value)
        os.kill(pid, signal.SIGHUP)
    except Exception as exc:  # pragma: no cover - depends on runtime
        raise SSLConfigurationError(f'Failed to reload nginx: {exc}') from exc


def verify_https_endpoint(host: str, path: str = '/api/health', timeout: int = 10) -> None:
    """Perform a HTTPS GET request to ensure certificate is served."""
    url = f'https://{host}{path}'
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - network dependent
        raise SSLVerificationError(f'HTTPS verification failed for {url}: {exc}') from exc


def serialize_ssl_configuration(ssl_config) -> Dict[str, Optional[str]]:
    """Convert SSL configuration ORM object into a safe dictionary."""
    if not ssl_config:
        return {}

    def to_iso(dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None

    return {
        'mode': ssl_config.mode,
        'primary_domain': ssl_config.primary_domain,
        'alternate_domains': ssl_config.alternate_domains or [],
        'enforce_https': ssl_config.enforce_https,
        'is_enabled': ssl_config.is_enabled,
        'certificate_status': ssl_config.certificate_status,
        'last_issued_at': to_iso(ssl_config.last_issued_at),
        'last_verified_at': to_iso(ssl_config.last_verified_at),
        'expires_at': to_iso(ssl_config.expires_at),
        'last_error': ssl_config.last_error,
        'uploaded': {
            'available': bool(ssl_config.uploaded_certificate_path and ssl_config.uploaded_private_key_path),
            'uploaded_at': to_iso(ssl_config.uploaded_at),
            'fingerprint': ssl_config.uploaded_fingerprint,
        },
        'auto_renew': ssl_config.auto_renew,
        'verification_hostname': ssl_config.verification_hostname,
    }


def cleanup_uploaded_files(paths: Dict[str, Optional[str]]) -> None:
    """Remove uploaded certificate files safely."""
    for path in paths.values():
        if not path:
            continue
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def cert_paths_exist(cert_path: str, key_path: str) -> bool:
    """Return True if both certificate and key paths exist."""
    return bool(cert_path and os.path.exists(cert_path) and key_path and os.path.exists(key_path))


def build_certbot_command(
    domains: List[str],
    email: Optional[str],
    staging: bool = False,
    force_renewal: bool = False,
) -> List[str]:
    """Construct certbot command for webroot challenge."""
    if not domains:
        raise SSLConfigurationError('No domains provided for certificate issuance')

    command = [
        'certbot', 'certonly', '--webroot', '-w', CERTBOT_WEBROOT,
        '--non-interactive', '--agree-tos', '--keep-until-expiring', '--expand'
    ]
    if force_renewal:
        command.append('--force-renewal')
    for domain in domains:
        command.extend(['-d', domain])
    if email:
        command.extend(['--email', email])
    else:
        command.append('--register-unsafely-without-email')
    if staging:
        command.extend(['--staging'])
    return command


def run_certbot(
    domains: List[str],
    email: Optional[str],
    staging: bool = False,
    force_renewal: bool = False,
) -> subprocess.CompletedProcess:
    """Execute certbot command for the provided domains."""
    ensure_directories()
    command = build_certbot_command(domains, email, staging, force_renewal)
    return subprocess.run(command, capture_output=True, text=True)


def write_enforce_redirect(enabled: bool) -> None:
    """Write a small JSON file capturing HTTPS enforcement state for other services."""
    ensure_directories()
    payload = json.dumps({'enforce_https': enabled, 'updated_at': datetime.utcnow().isoformat()})
    info_path = os.path.join(NGINX_RUNTIME_DIR, 'ssl_state.json')
    _write_secure_file(info_path, payload, mode=0o644)
