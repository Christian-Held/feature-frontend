from sqlalchemy import create_engine, inspect

from backend.db.base import Base
from backend.db.models import audit as _audit  # noqa: F401
from backend.db.models import billing as _billing  # noqa: F401
from backend.db.models import user as _user  # noqa: F401


def test_metadata_creates_all_tables(settings_env):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    expected_tables = {
        "users",
        "roles",
        "email_verifications",
        "password_resets",
        "sessions",
        "audit_logs",
        "spend_limits",
        "plans",
        "user_roles",
        "user_plans",
    }

    assert expected_tables.issubset(set(inspector.get_table_names()))
