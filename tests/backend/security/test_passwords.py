from backend.security.passwords import PasswordHashingService


def test_password_hashing_roundtrip(settings_env):
    service = PasswordHashingService(settings_env)
    password = "SuperSecret!"

    hashed_one = service.hash(password)
    hashed_two = service.hash(password)

    assert hashed_one != password
    assert hashed_two != password
    assert hashed_one != hashed_two
    assert service.verify(hashed_one, password)
    assert not service.verify(hashed_one, "WrongPassword")
