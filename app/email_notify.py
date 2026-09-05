"""Every outgoing email the app sends, all as FastAPI BackgroundTasks so
whichever request triggered one (a new booking, a customer editing their
own booking) returns immediately rather than waiting on an SMTP round
trip. See app/config.py for the SMTP_* environment variables these read.

Uses Python's built-in smtplib rather than a third-party email service
(SendGrid, Mailgun, etc.) — this is a low-volume booking form, not a bulk
mailer, so a normal Gmail account's SMTP server is more than enough and
needs no new paid account for the client to manage.

Every function here takes `booking` as a plain dict of field values, never
a SQLAlchemy Booking object — these run as background tasks, after the
request's database session has already been closed, so touching an ORM
object's attributes here could raise a detached-instance error the moment
something tries to lazily reload them.
"""

import smtplib
from email.message import EmailMessage

from .config import get_settings


def _send(subject: str, recipient_email: str, body: str) -> None:
    """Shared send path for every function below. Does nothing (and never
    raises) if SMTP isn't configured yet, so every feature that emails
    someone keeps working — minus the email — before the developer sets
    up SMTP_USERNAME/SMTP_PASSWORD. A delivery failure never surfaces to
    whoever triggered it, since there's no response left to report it
    through by the time this runs in the background; it's printed to the
    server log instead, flushed immediately so it shows up promptly in
    Railway's log stream rather than sitting in Python's stdout buffer.
    """
    settings = get_settings()
    if not settings.smtp_username or not settings.smtp_password:
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_username
    message["To"] = recipient_email
    message.set_content(body)

    try:
        # A short, explicit timeout so a network hiccup (or a host that
        # silently drops outbound SMTP traffic) fails fast in the
        # background rather than leaving the task hanging indefinitely.
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except Exception as exc:
        print(f"[email_notify] Failed to send to {recipient_email!r}: {exc}", flush=True)


def send_booking_notification(booking: dict, recipient_email: str, manage_url: str) -> None:
    """Emails the business's own address (site_settings.email) every time
    a customer submits the Book Us form. manage_url is included so staff
    can jump straight to the customer's own self-service page (e.g. to see
    exactly what the customer sees, or resend the link if asked) — the
    admin panel's own edit page is still the normal way to make changes."""
    _send(
        subject=f"New booking inquiry — {booking['name']} ({booking['event_type']})",
        recipient_email=recipient_email,
        body=f"""A new booking inquiry just came in through the website:

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
Customer's own self-service link (for reference/support): {manage_url}
""",
    )


def send_customer_confirmation(booking: dict, recipient_email: str, manage_url: str) -> None:
    """Emails the customer a confirmation of what they submitted, plus
    their personal manage_url — the only way (besides the one shown right
    after submitting the form) they'll ever get this link, since there's
    no customer login for them to retrieve it from later."""
    _send(
        subject="We've received your booking request",
        recipient_email=recipient_email,
        body=f"""Hi {booking['name']},

Thanks for booking with GPS Ushering and Events! Here's what we received:

Event type: {booking['event_type']}
Event date: {booking['event_date'] or "Not provided"}
Guest count: {booking['guest_count'] or "Not provided"}
Location: {booking['location'] or "Not provided"}

We'll be in touch shortly to confirm the details.

Need to change something before we confirm? Use your personal booking link:
{manage_url}

(Keep this link private — anyone with it can view or edit this booking.
Once we've confirmed your event, changes go through us directly.)
""",
    )


_STATUS_MESSAGES = {
    "contacted": "We've reached out about your booking and will follow up shortly to confirm the details.",
    "confirmed": "Great news — your event is confirmed! We're looking forward to it.",
    "completed": "Thank you for choosing GPS Ushering and Events — we hope your event went smoothly!",
    "cancelled": "Your booking has been cancelled. If this wasn't expected, please reach out to us directly.",
}


def send_booking_status_update(booking: dict, recipient_email: str, manage_url: str, new_status: str) -> None:
    """Emails the customer whenever the business owner moves their booking
    to a new status in the admin panel (see app/admin/routers/bookings.py)
    — otherwise a customer has no way to find out their event was
    confirmed (or cancelled) short of the business calling them directly.
    Not sent for "new", since that's the status a booking already starts
    at when send_customer_confirmation covers it."""
    if new_status not in _STATUS_MESSAGES:
        return
    _send(
        subject=f"Update on your booking — {booking['event_type']}",
        recipient_email=recipient_email,
        body=f"""Hi {booking['name']},

{_STATUS_MESSAGES[new_status]}

Event type: {booking['event_type']}
Event date: {booking['event_date'] or "Not provided"}

View or manage your booking here: {manage_url}
""",
    )


def send_password_reset_email(reset_url: str, recipient_email: str) -> None:
    """Emails the admin password-reset link. Unlike every other function
    in this file, there's no on-screen fallback for this one — showing
    the link directly to whoever clicked "forgot password" (the way the
    booking manage_url is shown right on the success page) would let
    anyone reset the admin password without ever proving they have access
    to the business's own email, which defeats the entire point. This
    feature only works once SMTP_USERNAME/SMTP_PASSWORD are actually set."""
    _send(
        subject="Reset your GPS Ushering admin password",
        recipient_email=recipient_email,
        body=f"""A password reset was requested for the GPS Ushering and Events admin panel.

Reset your password here (valid for 1 hour):
{reset_url}

If you didn't request this, you can safely ignore this email — your
password won't change unless the link above is used.
""",
    )


def send_customer_edit_notification(booking: dict, recipient_email: str, manage_url: str) -> None:
    """Emails the business's own address when a customer edits their own
    booking through the self-service link, so an update doesn't sit
    unnoticed until the next time someone happens to open the admin panel."""
    _send(
        subject=f"Booking updated by customer — {booking['name']} ({booking['event_type']})",
        recipient_email=recipient_email,
        body=f"""{booking['name']} just updated their own booking details:

Phone: {booking['phone']}
Email: {booking['email']}
Event type: {booking['event_type']}
Event date: {booking['event_date'] or "Not provided"}
Guest count: {booking['guest_count'] or "Not provided"}
Location: {booking['location'] or "Not provided"}

Message:
{booking['message'] or "(none)"}

Log in to the admin panel to review: {manage_url}
""",
    )
