"""Sends the business owner an email every time a customer submits the
Book Us form — see app/routers/bookings.py, which calls
send_booking_notification() as a FastAPI BackgroundTask so the customer's
form submission returns immediately without waiting on an SMTP round trip.

Uses Python's built-in smtplib rather than a third-party email service
(SendGrid, Mailgun, etc.) — this is a low-volume booking form, not a bulk
mailer, so a normal Gmail account's SMTP server is more than enough and
needs no new paid account for the client to manage. See app/config.py for
the SMTP_* environment variables this reads.
"""

import smtplib
from email.message import EmailMessage

from .config import get_settings


def send_booking_notification(booking: dict, recipient_email: str) -> None:
    """Emails a plain-text summary of a new booking to recipient_email
    (the business's own address — site_settings.email). `booking` is a
    plain dict of field values (see app/routers/bookings.py's call site),
    not a SQLAlchemy Booking object — this runs as a FastAPI background
    task, after the request's database session has already been closed,
    so touching an ORM object's attributes here could raise a detached-
    instance error the moment something tries to lazily reload them.

    Does nothing (and never raises) if SMTP isn't configured yet, so the
    booking form works fine before the developer sets up
    SMTP_USERNAME/SMTP_PASSWORD, and a delivery failure never surfaces as
    an error to the customer who just submitted the form — there's no
    response left to report a failure through by the time this runs. Any
    error is printed to the server log so it's still visible to whoever's
    watching deploy logs.
    """
    settings = get_settings()
    if not settings.smtp_username or not settings.smtp_password:
        return

    message = EmailMessage()
    message["Subject"] = f"New booking inquiry — {booking['name']} ({booking['event_type']})"
    message["From"] = settings.smtp_username
    message["To"] = recipient_email
    message.set_content(
        f"""A new booking inquiry just came in through the website:

Name: {booking['name']}
Phone: {booking['phone']}
Email: {booking['email']}
Event type: {booking['event_type']}
Event date: {booking['event_date'] or "Not provided"}
Guest count: {booking['guest_count'] or "Not provided"}
Location: {booking['location'] or "Not provided"}

Message:
{booking['message'] or "(none)"}

Log in to the admin panel to view and manage this booking.
"""
    )

    try:
        # A short, explicit timeout so a network hiccup (or a host that
        # silently drops outbound SMTP traffic) fails fast in the
        # background rather than leaving the task hanging indefinitely.
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except Exception as exc:
        # flush=True so this actually shows up promptly in Railway's log
        # stream rather than sitting in Python's stdout buffer.
        print(f"[email_notify] Failed to send booking notification: {exc}", flush=True)
