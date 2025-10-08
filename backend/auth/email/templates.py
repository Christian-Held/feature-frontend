"""Email templates for authentication flows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EmailContent:
    """Represents rendered email content."""

    subject: str
    text_body: str
    html_body: str


def render_verification_email(verification_url: str) -> EmailContent:
    """Create the email content for confirming a user's email address."""

    subject = "Bitte bestätige deine E-Mail"
    text_body = (
        "Willkommen bei Feature Auth!\n\n"
        "Bitte bestätige deine E-Mail-Adresse, indem du den folgenden Link öffnest:\n"
        f"{verification_url}\n\n"
        "Dieser Link ist 24 Stunden gültig. Danach verfällt die Registrierung automatisch.\n"
    )
    html_body = (
        "<p>Willkommen bei Feature Auth!</p>"
        "<p>Bitte bestätige deine E-Mail-Adresse, indem du auf den folgenden Link klickst:</p>"
        f'<p><a href="{verification_url}">{verification_url}</a></p>'
        "<p>Dieser Link ist 24 Stunden gültig. Danach verfällt die Registrierung automatisch.</p>"
    )
    return EmailContent(subject=subject, text_body=text_body, html_body=html_body)


def render_password_reset_email(reset_url: str) -> EmailContent:
    """Create the email content for password reset."""

    subject = "Passwort zurücksetzen"
    text_body = (
        "Hallo,\n\n"
        "Du hast angefordert, dein Passwort zurückzusetzen.\n\n"
        "Bitte setze dein Passwort zurück, indem du den folgenden Link öffnest:\n"
        f"{reset_url}\n\n"
        "Dieser Link ist 1 Stunde gültig.\n\n"
        "Falls du diese Anfrage nicht gestellt hast, ignoriere diese E-Mail einfach.\n"
    )
    html_body = (
        "<p>Hallo,</p>"
        "<p>Du hast angefordert, dein Passwort zurückzusetzen.</p>"
        "<p>Bitte setze dein Passwort zurück, indem du auf den folgenden Link klickst:</p>"
        f'<p><a href="{reset_url}">{reset_url}</a></p>'
        "<p>Dieser Link ist 1 Stunde gültig.</p>"
        "<p>Falls du diese Anfrage nicht gestellt hast, ignoriere diese E-Mail einfach.</p>"
    )
    return EmailContent(subject=subject, text_body=text_body, html_body=html_body)


__all__ = ["EmailContent", "render_verification_email", "render_password_reset_email"]
