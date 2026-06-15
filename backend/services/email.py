"""Email service — aiosmtplib over Gmail SMTP (STARTTLS, port 587).

No payment is taken online. Order/booking emails notify the owner, who then
contacts the customer to confirm availability and arrange payment. Every send
is wrapped in try/except so a mail failure never crashes a request.
"""
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
# CRITICAL: Gmail app passwords are displayed with spaces — strip them.
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "")

OWNER_EMAIL      = os.getenv("OWNER_EMAIL", "saleshuntingandfishingsupplyco@gmail.com")
BUSINESS_NAME    = os.getenv("BUSINESS_NAME", "Hunting & Fishing Supply Co")
OWNER_PHONE      = os.getenv("OWNER_PHONE", "+14062069144")
PHONE_DISPLAY    = "+1 (406) 206-9144"
WHATSAPP         = os.getenv("WHATSAPP", "+16016013408")
BUSINESS_ADDRESS = os.getenv("BUSINESS_ADDRESS", "2667 Jackson Ave, Memphis, TN 38108")

DARK  = "#0e1a0e"
AMBER = "#e28a00"
GREY  = "#888878"


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _base_html(title: str, body: str) -> str:
    """Wrap body HTML in the branded shell (header + footer)."""
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;background:#f2f1ec;font-family:Arial,Helvetica,sans-serif;color:#1a1a1a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f2f1ec;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="max-width:620px;background:#ffffff;border-radius:6px;overflow:hidden;">
        <!-- Header -->
        <tr><td style="background:{DARK};padding:26px 32px;">
          <div style="font-size:22px;font-weight:bold;color:{AMBER};letter-spacing:.5px;">{BUSINESS_NAME}</div>
          <div style="font-size:12px;color:{GREY};margin-top:4px;letter-spacing:2px;text-transform:uppercase;">Hunt. Fish. Gear Up.</div>
        </td></tr>
        <!-- Title bar -->
        <tr><td style="background:{AMBER};padding:12px 32px;color:{DARK};font-weight:bold;font-size:15px;">{title}</td></tr>
        <!-- Body -->
        <tr><td style="padding:28px 32px;font-size:14px;line-height:1.6;color:#222;">{body}</td></tr>
        <!-- Footer -->
        <tr><td style="background:{DARK};padding:22px 32px;color:{GREY};font-size:12px;line-height:1.7;">
          <div style="color:{AMBER};font-weight:bold;font-size:13px;">{BUSINESS_NAME}</div>
          {BUSINESS_ADDRESS}<br>
          Phone: {PHONE_DISPLAY}<br>
          {OWNER_EMAIL}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _rows(pairs) -> str:
    """Build label/value table rows, skipping empty values."""
    out = []
    for label, value in pairs:
        if value in (None, "", []):
            continue
        out.append(
            f'<tr>'
            f'<td style="padding:6px 12px 6px 0;color:{GREY};white-space:nowrap;vertical-align:top;">{label}</td>'
            f'<td style="padding:6px 0;color:#1a1a1a;"><strong>{value}</strong></td>'
            f'</tr>'
        )
    return '<table role="presentation" cellpadding="0" cellspacing="0">' + "".join(out) + "</table>"


def _items_table(items, shipping: float) -> str:
    """Build an itemized order table with subtotal/shipping/total."""
    subtotal = sum(i["unit_price"] * i["quantity"] for i in items)
    grand = subtotal + shipping
    rows = []
    for i in items:
        line = i["unit_price"] * i["quantity"]
        model = i.get("model_number") or ""
        rows.append(
            f'<tr style="border-bottom:1px solid #eee;">'
            f'<td style="padding:8px 6px;">{i["name"]}'
            + (f'<br><span style="color:{GREY};font-size:12px;">{model}</span>' if model else "")
            + f'</td>'
            f'<td style="padding:8px 6px;text-align:center;">{i["quantity"]}</td>'
            f'<td style="padding:8px 6px;text-align:right;">{_money(i["unit_price"])}</td>'
            f'<td style="padding:8px 6px;text-align:right;">{_money(line)}</td>'
            f'</tr>'
        )
    ship_label = "FREE" if shipping == 0 else _money(shipping)
    return f"""\
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:8px 0 4px;font-size:13px;">
  <tr style="background:#f2f1ec;text-align:left;">
    <th style="padding:8px 6px;">Product</th>
    <th style="padding:8px 6px;text-align:center;">Qty</th>
    <th style="padding:8px 6px;text-align:right;">Unit</th>
    <th style="padding:8px 6px;text-align:right;">Subtotal</th>
  </tr>
  {''.join(rows)}
  <tr><td colspan="3" style="padding:8px 6px;text-align:right;">Subtotal</td><td style="padding:8px 6px;text-align:right;">{_money(subtotal)}</td></tr>
  <tr><td colspan="3" style="padding:4px 6px;text-align:right;">Shipping</td><td style="padding:4px 6px;text-align:right;">{ship_label}</td></tr>
  <tr style="background:{DARK};color:{AMBER};font-weight:bold;">
    <td colspan="3" style="padding:10px 6px;text-align:right;">GRAND TOTAL</td>
    <td style="padding:10px 6px;text-align:right;">{_money(grand)}</td>
  </tr>
</table>"""


async def _send(to: str, subject: str, html: str) -> bool:
    """Send an HTML email. Never raises — logs and returns False on failure."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[email:skipped] SMTP not configured — would send '{subject}' to {to}",
              flush=True)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{BUSINESS_NAME} <{SMTP_USER}>"
        msg["To"] = to
        msg.attach(MIMEText(html, "html"))
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        print(f"[email:sent] '{subject}' -> {to}", flush=True)
        return True
    except Exception as exc:  # noqa: BLE001 — must never crash the request.
        print(f"[email:error] {exc} (subject='{subject}', to={to})", flush=True)
        return False


# ─────────────────────────── Booking emails ───────────────────────────

async def send_customer_confirmation(booking: dict) -> None:
    name = booking.get("first_name", "")
    product = booking.get("product_interest") or booking.get("service") or "your inquiry"
    body = f"""\
<p>Hi {name},</p>
<p>Thank you for reaching out to {BUSINESS_NAME}. We've received your inquiry about
<strong>{product}</strong> and our team will reach out within a few hours via your
preferred contact method.</p>
{_rows([
    ("Product / Interest", booking.get("product_interest")),
    ("Service", booking.get("service")),
    ("Details", booking.get("details")),
])}
<p style="margin-top:18px;">Need something urgently? Call us at <strong>{PHONE_DISPLAY}</strong>
or email us at <strong>{OWNER_EMAIL}</strong>.</p>
<p>— The {BUSINESS_NAME} Team</p>"""
    await _send(
        booking.get("email", ""),
        f"We received your inquiry — {BUSINESS_NAME}",
        _base_html("Inquiry Received", body),
    )


async def send_owner_notification(booking: dict) -> None:
    name = f"{booking.get('first_name','')} {booking.get('last_name','')}".strip()
    product = booking.get("product_interest") or "General Inquiry"
    body = f"""\
<p style="font-size:16px;"><strong>New inquiry — contact the customer.</strong></p>
{_rows([
    ("Name", name),
    ("Phone", booking.get("phone")),
    ("Email", booking.get("email")),
    ("Product / Interest", booking.get("product_interest")),
    ("Service", booking.get("service")),
    ("Details", booking.get("details")),
])}
<p style="margin-top:16px;color:{GREY};">Reach the customer at the phone or email above.</p>"""
    await _send(
        OWNER_EMAIL,
        f"New Inquiry from {name} — {product}",
        _base_html("New Customer Inquiry", body),
    )


# ──────────────────────────── Order emails ────────────────────────────

async def send_order_customer_confirmation(customer: dict, items: list,
                                           total: float, shipping: float) -> None:
    name = customer.get("first_name", "")
    pay = customer.get("payment_method")
    pay_hint = f" for <strong>{pay}</strong>" if pay else ""
    body = f"""\
<p>Thank you {name}! We've received your order.</p>
{_items_table(items, shipping)}
<p>Our team will contact you within a few hours at
<strong>{customer.get('phone','')}</strong> or <strong>{customer.get('email','')}</strong>
to confirm availability and arrange payment.</p>
<p style="margin-top:14px;">Questions now? Call <strong>{PHONE_DISPLAY}</strong>
or email <strong>{OWNER_EMAIL}</strong>.</p>
<p>— The {BUSINESS_NAME} Team</p>"""
    await _send(
        customer.get("email", ""),
        f"Order Received — {BUSINESS_NAME}",
        _base_html("Order Received", body),
    )


async def send_order_owner_notification(customer: dict, items: list,
                                        total: float, shipping: float) -> None:
    name = f"{customer.get('first_name','')} {customer.get('last_name','')}".strip()
    body = f"""\
<p style="font-size:16px;color:#b5413a;"><strong>NEW ORDER — CONTACT CUSTOMER TO CONFIRM AND ARRANGE PAYMENT</strong></p>
{_rows([
    ("Name", name),
    ("Phone", customer.get("phone")),
    ("Email", customer.get("email")),
    ("Company", customer.get("company")),
    ("Address", customer.get("address")),
    ("City", customer.get("city")),
    ("State", customer.get("state")),
    ("ZIP", customer.get("zip")),
    ("Country", customer.get("country")),
    ("Freight Region", customer.get("freight_region")),
    ("Contact Preference", customer.get("contact_pref")),
    ("Best Time", customer.get("best_time")),
    ("Preferred Payment", customer.get("payment_method")),
    ("Notes", customer.get("notes")),
])}
{_items_table(items, shipping)}
<p style="margin-top:14px;"><strong>Next step:</strong> Contact the customer at
{customer.get('phone','')} / {customer.get('email','')} to confirm availability and
send payment instructions.</p>"""
    grand = sum(i["unit_price"] * i["quantity"] for i in items) + shipping
    await _send(
        OWNER_EMAIL,
        f"NEW ORDER from {name} — {_money(grand)} — ACTION REQUIRED",
        _base_html("New Order — Action Required", body),
    )
