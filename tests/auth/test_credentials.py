from datetime import datetime, timedelta, timezone

from src.auth.credentials import TokenData, TokenStorage


def test_from_token_response_without_refresh_token():
    """Polar Accesslink no siempre devuelve refresh_token (tokens de larga duración)."""
    payload = {
        "access_token": "abc123",
        "token_type": "bearer",
        "expires_in": 315360000,
        "x_user_id": 64507128,
    }

    token = TokenData.from_token_response(payload)

    assert token.access_token == "abc123"
    assert token.refresh_token is None
    assert token.x_user_id == 64507128


def test_from_token_response_with_refresh_token():
    payload = {
        "access_token": "abc123",
        "refresh_token": "ref456",
        "expires_in": 3600,
    }

    token = TokenData.from_token_response(payload)

    assert token.refresh_token == "ref456"


def test_token_not_expired_when_far_in_future():
    token = TokenData(
        access_token="abc",
        expires_at=datetime.now(timezone.utc) + timedelta(days=365),
    )
    assert token.is_expired() is False


def test_token_expired_when_in_the_past():
    token = TokenData(
        access_token="abc",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    assert token.is_expired() is True


def test_token_expired_within_safety_margin():
    """A 1 minuto de caducar ya se considera caducado (margen de seguridad de 2 min)."""
    token = TokenData(
        access_token="abc",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    assert token.is_expired() is True


def test_storage_round_trip(tmp_path):
    storage_path = tmp_path / "tokens.json"
    storage = TokenStorage(storage_path)

    token = TokenData(
        access_token="abc",
        x_user_id=42,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    storage.save(token)

    loaded = storage.load()
    assert loaded is not None
    assert loaded.access_token == "abc"
    assert loaded.x_user_id == 42


def test_storage_load_returns_none_when_file_missing(tmp_path):
    storage = TokenStorage(tmp_path / "missing.json")
    assert storage.load() is None


def test_storage_load_returns_none_when_file_corrupted(tmp_path):
    path = tmp_path / "tokens.json"
    path.write_text("not valid json")
    storage = TokenStorage(path)
    assert storage.load() is None


def test_storage_clear_removes_file(tmp_path):
    path = tmp_path / "tokens.json"
    storage = TokenStorage(path)
    storage.save(TokenData(access_token="abc", expires_at=datetime.now(timezone.utc)))

    assert path.exists()
    storage.clear()
    assert not path.exists()
