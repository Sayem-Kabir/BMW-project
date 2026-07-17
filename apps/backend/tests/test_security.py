"""Risk engine unit tests — full suite in Phase 4."""

from app.core.security import create_access_token, get_password_hash, verify_password


def test_password_hash_roundtrip():
    hashed = get_password_hash("test-password-123")
    assert verify_password("test-password-123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_created():
    token = create_access_token("user-123")
    assert isinstance(token, str)
    assert len(token) > 20
