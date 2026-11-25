from datetime import datetime
import pytest
from app.main import app
from app.core.auth import get_current_user
from app.core.tenancy import require_device_credential, DeviceCredential
from app.models.users import UserInDB


def override_get_current_user():
    return UserInDB(
        user_id=1,
        username="testuser",
        uid_linux=1000,
        password_hash="",
        created_at=datetime(2026, 1, 1),
        is_admin=False,
    )


def override_require_device_credential():
    return DeviceCredential(device_id="test-host", workspace_id=1)


@pytest.fixture(autouse=True)
def bypass_auth():
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_device_credential] = override_require_device_credential
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_device_credential, None)
