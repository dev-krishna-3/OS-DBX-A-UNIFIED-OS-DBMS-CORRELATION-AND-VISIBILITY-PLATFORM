import pytest
from app.main import app
from app.core.auth import get_current_user

def override_get_current_user():
    return {"username": "testuser", "uid_linux": 1000}

@pytest.fixture(autouse=True)
def bypass_auth():
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
