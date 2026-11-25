"""Tests for Option A split-cloud deployment configuration and schema bootstrap utilities."""

from pathlib import Path

from app.config import database as db_module
from app.config.settings import Settings
from app.services.schema_bootstrap import split_sql_statements


def test_cors_origins_parses_comma_separated_and_json():
    s_csv = Settings(cors_origins="https://demo.vercel.app/, https://preview.vercel.app ")
    assert s_csv.cors_origins == ["https://demo.vercel.app", "https://preview.vercel.app"]

    s_json = Settings(cors_origins='["https://one.pages.dev/", "https://two.pages.dev"]')
    assert s_json.cors_origins == ["https://one.pages.dev", "https://two.pages.dev"]

    s_empty = Settings(cors_origins="")
    assert s_empty.cors_origins == []


def test_mysql_connect_kwargs_timeout_and_pem(monkeypatch):
    fake = Settings(
        mysql_host="db.example.com",
        mysql_port=25060,
        mysql_user="avnadmin",
        mysql_password="secret-password",
        mysql_database="defaultdb",
        mysql_connect_timeout=12,
        mysql_ssl_ca_pem="-----BEGIN CERTIFICATE-----\\nTEST\\n-----END CERTIFICATE-----",
    )
    monkeypatch.setattr(db_module, "settings", fake)
    monkeypatch.setattr(db_module, "_connect_host", fake.mysql_host)
    monkeypatch.setattr(db_module, "_cached_ssl_ca_path", None)

    kwargs = db_module.get_mysql_connect_kwargs()
    assert kwargs["connection_timeout"] == 12
    assert kwargs["ssl_verify_cert"] is True
    assert kwargs["ssl_disabled"] is False
    ca_file = Path(kwargs["ssl_ca"])
    assert ca_file.is_file()
    assert "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n" == ca_file.read_text(encoding="utf-8")
    ca_file.unlink(missing_ok=True)


def test_split_sql_statements_handles_schema_and_migration_003():
    repo_root = Path(__file__).resolve().parents[2]
    schema_sql = (repo_root / "database" / "schema.sql").read_text(encoding="utf-8")
    mig_sql = (repo_root / "database" / "migrations" / "003_add_workspace_and_device_identity.sql").read_text(
        encoding="utf-8"
    )

    base_stmts = split_sql_statements(schema_sql)
    mig_stmts = split_sql_statements(mig_sql)

    assert len(base_stmts) >= 38
    assert all(not s.startswith("#") and not s.startswith("--") for s in base_stmts)
    assert len(mig_stmts) >= 20
    assert any("INSERT INTO workspaces" in s for s in mig_stmts)
