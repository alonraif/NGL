import os
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

import ssl_service
from ssl_service import (
    SSLConfigurationError,
    cleanup_uploaded_files,
    is_valid_domain,
    normalize_domains,
    store_uploaded_material,
    validate_certificate_pair,
)


def _generate_self_signed(subject_cn: str = 'example.com'):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, 'California'),
        x509.NameAttribute(NameOID.LOCALITY_NAME, 'San Francisco'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'NGL Test Suite'),
        x509.NameAttribute(NameOID.COMMON_NAME, subject_cn),
    ])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow() - timedelta(days=1))
        .not_valid_after(datetime.utcnow() + timedelta(days=10))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(subject_cn)]), critical=False)
    )
    certificate = builder.sign(private_key=key, algorithm=hashes.SHA256())
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode('utf-8')
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')
    return cert_pem, key_pem


def test_validate_certificate_pair_matches_private_key():
    cert_pem, key_pem = _generate_self_signed()
    metadata = validate_certificate_pair(cert_pem, key_pem)
    assert metadata.fingerprint_sha256
    assert isinstance(metadata.expires_at, datetime)
    assert metadata.expires_at.tzinfo is timezone.utc


def test_validate_certificate_pair_mismatch_raises():
    cert_pem, _ = _generate_self_signed()
    _, other_key = _generate_self_signed('other.example.com')
    with pytest.raises(SSLConfigurationError):
        validate_certificate_pair(cert_pem, other_key)


def test_domain_helpers_normalize_and_validate():
    domains = normalize_domains('Example.com', ['www.example.com', 'Example.com'])
    assert domains == ['example.com', 'www.example.com']
    assert is_valid_domain('api.example.com')
    assert not is_valid_domain('not a domain')
    assert not is_valid_domain('-invalid.example.com')


def test_store_uploaded_material_writes_files(tmp_path, monkeypatch):
    cert_dir = tmp_path / 'ssl'
    cert_dir.mkdir()
    monkeypatch.setattr(ssl_service, 'UPLOAD_CERT_DIR', str(cert_dir))
    monkeypatch.setattr(ssl_service, 'CERTBOT_WEBROOT', str(tmp_path / 'webroot'))
    monkeypatch.setattr(ssl_service, 'NGINX_RUNTIME_DIR', str(tmp_path / 'runtime'))
    cert_pem, key_pem = _generate_self_signed()
    paths = store_uploaded_material(cert_pem, key_pem)
    assert os.path.exists(paths['certificate_path'])
    assert os.path.exists(paths['private_key_path'])
    cleanup_uploaded_files(paths)
    assert not os.path.exists(paths['certificate_path'])
    assert not os.path.exists(paths['private_key_path'])
