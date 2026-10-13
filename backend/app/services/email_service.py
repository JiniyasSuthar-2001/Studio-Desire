import os
import smtplib
import json
import ssl
import html
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

try:
    from app.database.session import SessionLocal
    from app.models.content import SiteContent
    from app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment
except ImportError:
    from backend.app.database.session import SessionLocal
    from backend.app.models.content import SiteContent
    from backend.app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment

logger = logging.getLogger("studio_desire.email")

DEFAULT_EMAIL_SETTINGS = {
    "sender_name": "Studio Desire",
    "sender_email": "studiodesire01@gmail.com",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "security": "TLS",
    "smtp_username": "",
    "smtp_password": "",
    "recipients": ["studiodesire01@gmail.com"],
    "send_customer_confirmation": True
}


def get_email_settings() -> Dict[str, Any]:
    """Load email settings from database, falling back to defaults."""
    db = SessionLocal()
    try:
        record = db.query(SiteContent).filter(SiteContent.section == "email_settings").first()
        if record and record.content_json:
            try:
                data = json.loads(record.content_json)
                merged = dict(DEFAULT_EMAIL_SETTINGS)
                merged.update(data)
                return merged
            except Exception as e:
                logger.warning(f"Error parsing email settings from database: {e}")
        return dict(DEFAULT_EMAIL_SETTINGS)
    finally:
        db.close()


def save_email_settings(settings: Dict[str, Any], updated_by: str = "Owner") -> None:
    """Save email settings to database securely."""
    db = SessionLocal()
    try:
        record = db.query(SiteContent).filter(SiteContent.section == "email_settings").first()
        if not record:
            record = SiteContent(
                section="email_settings",
                content_json=json.dumps(settings),
                updated_by=updated_by
            )
            db.add(record)
        else:
            # Preserve existing password if not provided or empty in incoming settings
            if not settings.get("smtp_password"):
                try:
                    current_data = json.loads(record.content_json)
                    settings["smtp_password"] = current_data.get("smtp_password", "")
                except Exception:
                    pass
            record.content_json = json.dumps(settings)
            record.updated_by = updated_by
        db.commit()
    finally:
        db.close()


def send_smtp_message(
    to_emails: List[str],
    subject: str,
    text_content: str,
    html_content: str,
    settings_override: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Sends an email using the configured SMTP server.
    Returns (success: bool, error_message: Optional[str]).
    Never logs or exposes passwords.
    """
    # Environment flag to avoid real network calls during automated testing
    if os.getenv("TESTING_DISABLE_SMTP", "false").lower() == "true":
        logger.info(f"[TEST MODE] Simulated email dispatch to: {to_emails} | Subject: {subject}")
        return True, None

    cfg = settings_override or get_email_settings()

    smtp_host = cfg.get("smtp_host", "").strip()
    smtp_port = int(cfg.get("smtp_port", 587))
    security = cfg.get("security", "TLS").strip().upper()
    username = cfg.get("smtp_username", "").strip()
    password = cfg.get("smtp_password", "").strip()
    sender_name = cfg.get("sender_name", "Studio Desire").strip()
    sender_email = cfg.get("sender_email", "").strip() or username

    if not smtp_host or not username:
        return False, "SMTP configuration incomplete: SMTP host and username are required."

    valid_recipients = [e.strip() for e in to_emails if e and "@" in e]
    if not valid_recipients:
        return False, "No valid recipient email addresses provided."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = ", ".join(valid_recipients)

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        if security == "SSL":
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            if security == "TLS":
                context = ssl.create_default_context()
                server.starttls(context=context)

        if username and password:
            server.login(username, password)

        server.sendmail(sender_email, valid_recipients, msg.as_string())
        server.quit()
        logger.info(f"Email successfully dispatched to {valid_recipients} (Subject: '{subject}')")
        return True, None
    except Exception as e:
        logger.error(f"SMTP delivery failure to {valid_recipients} via {smtp_host}:{smtp_port} - {type(e).__name__}: {str(e)}")
        return False, f"SMTP delivery failed: {type(e).__name__} ({str(e)})"


def send_owner_enquiry_notification(enquiry: ProjectEnquiry) -> Tuple[bool, Optional[str]]:
    """
    Sends professional architectural notification email to configured Studio Desire recipients.
    All user-submitted parameters are strictly HTML-escaped.
    """
    cfg = get_email_settings()
    recipients = cfg.get("recipients", [])
    if not recipients:
        recipients = [cfg.get("sender_email", "studiodesire01@gmail.com")]

    subject = f"New Project Enquiry — {enquiry.name} — {enquiry.project_type}"
    date_str = enquiry.created_at.strftime("%d %b %Y, %H:%M IST") if enquiry.created_at else "Today"

    # HTML-escaped user inputs to eliminate HTML injection / XSS
    esc_name = html.escape(str(enquiry.name or ""))
    esc_email = html.escape(str(enquiry.email or ""))
    esc_phone = html.escape(str(enquiry.phone or ""))
    esc_type = html.escape(str(enquiry.project_type or ""))
    esc_location = html.escape(str(enquiry.location or "Not specified"))
    esc_budget = html.escape(str(enquiry.budget or "Not specified"))
    esc_timeline = html.escape(str(enquiry.timeline or "Not specified"))
    esc_source = html.escape(str(enquiry.source or "planning").upper())
    esc_message = html.escape(str(enquiry.message or ""))
    esc_ref = html.escape(str(enquiry.reference_number or ""))

    # Build attachments list text & escaped HTML
    attachments = getattr(enquiry, "attachments", [])
    att_list_text = "None attached"
    att_list_html = "<em>None attached</em>"
    if attachments:
        att_lines = []
        html_lines = []
        for a in attachments:
            size_kb = max(1, round(a.file_size / 1024))
            esc_fn = html.escape(str(a.original_filename or "File"))
            esc_ft = html.escape(str(a.file_type or "file").upper())
            att_lines.append(f"- {a.original_filename} ({a.file_type.upper()}, {size_kb} KB)")
            html_lines.append(f"<li><strong>{esc_fn}</strong> — {esc_ft} ({size_kb} KB)</li>")
        att_list_text = "\n".join(att_lines)
        att_list_html = f"<ul>{''.join(html_lines)}</ul>"

    # Plain text format
    text_body = f"""STUDIO DESIRE
NEW PROJECT ENQUIRY

A new project enquiry has been submitted through the Studio Desire website.

────────────────────────────────────────────────────────────
CLIENT
Name:    {enquiry.name}
Email:   {enquiry.email}
Phone:   {enquiry.phone}

────────────────────────────────────────────────────────────
PROJECT
Type:     {enquiry.project_type}
Location: {enquiry.location or "Not specified"}
Budget:   {enquiry.budget or "Not specified"}
Timeline: {enquiry.timeline or "Not specified"}
Source:   {(enquiry.source or "").upper()}

────────────────────────────────────────────────────────────
PROJECT BRIEF
{enquiry.message}

────────────────────────────────────────────────────────────
ATTACHMENTS
{att_list_text}

────────────────────────────────────────────────────────────
SUBMITTED
Date:      {date_str}
Reference: {enquiry.reference_number}

────────────────────────────────────────────────────────────
OPEN IN OWNER DASHBOARD:
http://localhost:5173/#admin

Studio Desire — Architecture & Interior Design
"""

    # Editorial HTML format
    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f7f6f4; color: #141413; padding: 24px; }}
    .card {{ max-width: 620px; margin: 0 auto; background: #ffffff; border: 1px solid #e2ded8; padding: 36px 32px; }}
    .header {{ border-bottom: 2px solid #141413; padding-bottom: 16px; margin-bottom: 24px; }}
    .brand {{ font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: #767571; }}
    .title {{ font-family: Georgia, serif; font-size: 24px; font-weight: 300; letter-spacing: 0.02em; margin: 8px 0 0 0; text-transform: uppercase; }}
    .section-title {{ font-size: 10px; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; color: #9c9992; margin-top: 24px; margin-bottom: 8px; border-bottom: 1px solid #f0ede8; padding-bottom: 4px; }}
    .meta-row {{ margin: 6px 0; font-size: 14px; line-height: 1.5; }}
    .label {{ color: #767571; width: 90px; display: inline-block; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .val {{ color: #141413; font-weight: 500; }}
    .brief-box {{ background: #faf9f7; border: 1px solid #ebe7e1; padding: 16px; font-size: 14px; line-height: 1.6; color: #222; margin-top: 8px; white-space: pre-wrap; }}
    .btn {{ display: inline-block; background: #141413; color: #ffffff !important; padding: 12px 24px; text-decoration: none; font-size: 12px; letter-spacing: 0.15em; text-transform: uppercase; font-weight: 600; margin-top: 28px; }}
    .footer {{ margin-top: 32px; font-size: 11px; color: #9c9992; letter-spacing: 0.08em; border-top: 1px solid #f0ede8; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="brand">Studio Desire — Project Enquiry System</div>
      <h1 class="title">New Project Enquiry</h1>
    </div>

    <div class="section-title">Client Details</div>
    <div class="meta-row"><span class="label">Name:</span> <span class="val">{esc_name}</span></div>
    <div class="meta-row"><span class="label">Email:</span> <span class="val"><a href="mailto:{esc_email}">{esc_email}</a></span></div>
    <div class="meta-row"><span class="label">Phone:</span> <span class="val"><a href="tel:{esc_phone}">{esc_phone}</a></span></div>

    <div class="section-title">Project Specifications</div>
    <div class="meta-row"><span class="label">Type:</span> <span class="val">{esc_type}</span></div>
    <div class="meta-row"><span class="label">Location:</span> <span class="val">{esc_location}</span></div>
    <div class="meta-row"><span class="label">Budget:</span> <span class="val">{esc_budget}</span></div>
    <div class="meta-row"><span class="label">Timeline:</span> <span class="val">{esc_timeline}</span></div>
    <div class="meta-row"><span class="label">Source:</span> <span class="val">{esc_source}</span></div>

    <div class="section-title">Project Brief</div>
    <div class="brief-box">{esc_message}</div>

    <div class="section-title">Submitted Attachments</div>
    {att_list_html}

    <div class="section-title">Submission Metadata</div>
    <div class="meta-row"><span class="label">Date:</span> <span class="val">{date_str}</span></div>
    <div class="meta-row"><span class="label">Reference:</span> <span class="val"><strong>{esc_ref}</strong></span></div>

    <div>
      <a href="http://localhost:5173/#admin" class="btn">Open In Owner Dashboard →</a>
    </div>

    <div class="footer">
      Studio Desire Architecture & Interiors · Ahmedabad, Gujarat
    </div>
  </div>
</body>
</html>"""

    return send_smtp_message(recipients, subject, text_body, html_body)


def send_customer_confirmation(enquiry: ProjectEnquiry) -> Tuple[bool, Optional[str]]:
    """
    Sends clean confirmation email to the customer acknowledging receipt of their enquiry.
    All user inputs are safely escaped.
    """
    cfg = get_email_settings()
    if not cfg.get("send_customer_confirmation", True):
        return True, None

    esc_name = html.escape(str(enquiry.name or "Valued Client"))
    esc_ref = html.escape(str(enquiry.reference_number or ""))
    esc_type = html.escape(str(enquiry.project_type or ""))

    subject = f"Studio Desire — Project Enquiry Received ({enquiry.reference_number})"

    text_body = f"""Hello {enquiry.name},

Thank you for sharing your project with Studio Desire.

We have received your project enquiry and any submitted reference material.

Reference: {enquiry.reference_number}
Project Scope: {enquiry.project_type}

We will review the spatial requirements and contact you using the details you provided.

Thank you,

Studio Desire
Architecture & Interior Design
studiodesire01@gmail.com
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f7f6f4; color: #141413; padding: 24px; }}
    .card {{ max-width: 580px; margin: 0 auto; background: #ffffff; border: 1px solid #e2ded8; padding: 36px 32px; }}
    .header {{ border-bottom: 2px solid #141413; padding-bottom: 14px; margin-bottom: 24px; }}
    .brand {{ font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: #767571; }}
    .title {{ font-family: Georgia, serif; font-size: 22px; font-weight: 300; letter-spacing: 0.02em; margin: 8px 0 0 0; text-transform: uppercase; }}
    .content {{ font-size: 14px; line-height: 1.7; color: #2a2927; }}
    .badge-box {{ background: #faf9f7; border: 1px solid #ebe7e1; padding: 14px 18px; margin: 20px 0; }}
    .ref-label {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.15em; color: #767571; }}
    .ref-val {{ font-size: 18px; font-weight: 600; color: #141413; margin-top: 4px; }}
    .footer {{ margin-top: 32px; font-size: 11px; color: #9c9992; letter-spacing: 0.08em; border-top: 1px solid #f0ede8; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="brand">Studio Desire</div>
      <h1 class="title">Project Enquiry Received</h1>
    </div>

    <div class="content">
      <p>Hello <strong>{esc_name}</strong>,</p>
      <p>Thank you for sharing your project with Studio Desire. We have received your project enquiry and any accompanying rough designs, drawings, or reference materials.</p>

      <div class="badge-box">
        <div class="ref-label">Enquiry Reference Number</div>
        <div class="ref-val">{esc_ref}</div>
        <div style="font-size: 12px; color: #767571; margin-top: 4px;">Project Scope: {esc_type}</div>
      </div>

      <p>Our studio team will review the information provided and contact you using the details submitted.</p>

      <p style="margin-top: 24px;">Sincerely,<br><strong>Studio Desire</strong><br><em>Architecture & Interior Design</em></p>
    </div>

    <div class="footer">
      Studio Desire · Ahmedabad, Gujarat, India · studiodesire01@gmail.com
    </div>
  </div>
</body>
</html>"""

    return send_smtp_message([enquiry.email], subject, text_body, html_body)
