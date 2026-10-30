"""管理员判定单测。"""

from app.config import settings
from app.core.roles import admin_emails, is_admin_email


def test_admin_emails_parsing(monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "a@x.com, B@Y.com ,, ")
    assert admin_emails() == {"a@x.com", "b@y.com"}


def test_is_admin_email(monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "admin@example.com")
    assert is_admin_email("admin@example.com") is True
    assert is_admin_email("ADMIN@example.com") is True
    assert is_admin_email("user@example.com") is False
    assert is_admin_email(None) is False


def test_is_admin_empty_config(monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "")
    assert is_admin_email("anyone@example.com") is False
