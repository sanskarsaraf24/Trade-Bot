"""
Email alerting service via SMTP (Minpay mail server).
Sends trade alerts, daily reports, and error notifications.
"""
import asyncio
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_trade_email(event: str, symbol: str, signal: str,
                       price: float, pnl: float = 0, reason: str = "") -> tuple[str, str]:
    """Returns (subject, html_body)."""
    emoji = "🟢" if pnl >= 0 else "🔴"
    subject = f"[Trading Bot] {emoji} {event}: {symbol} {signal}"
    body = f"""
    <html><body style="font-family: sans-serif; padding: 20px; background: #0f172a; color: #e2e8f0;">
      <div style="max-width: 500px; margin: auto; background: #1e293b; border-radius: 12px; padding: 24px;">
        <h2 style="color: #6366f1; margin-bottom: 4px;">📊 Trade Alert</h2>
        <p style="color: #94a3b8; font-size: 13px;">{datetime.now().strftime('%d %b %Y, %I:%M %p IST')}</p>
        <hr style="border-color: #334155; margin: 16px 0;" />
        <table style="width: 100%; border-collapse: collapse;">
          <tr><td style="padding: 6px 0; color: #94a3b8;">Event</td><td style="text-align:right; font-weight:bold;">{event}</td></tr>
          <tr><td style="padding: 6px 0; color: #94a3b8;">Symbol</td><td style="text-align:right; font-weight:bold;">{symbol}</td></tr>
          <tr><td style="padding: 6px 0; color: #94a3b8;">Signal</td><td style="text-align:right; font-weight:bold;">{signal}</td></tr>
          <tr><td style="padding: 6px 0; color: #94a3b8;">Price</td><td style="text-align:right;">₹{price:,.2f}</td></tr>
          <tr><td style="padding: 6px 0; color: #94a3b8;">P&L</td>
              <td style="text-align:right; color:{'#22c55e' if pnl >= 0 else '#ef4444'}; font-weight:bold;">₹{pnl:,.2f}</td></tr>
          {'<tr><td style="padding: 6px 0; color: #94a3b8;">Reason</td><td style="text-align:right;">' + reason + '</td></tr>' if reason else ''}
        </table>
        <hr style="border-color: #334155; margin: 16px 0;" />
        <p style="font-size: 11px; color: #475569; text-align: center;">
          LLM Trading Bot · trade.sanskarsaraf.in
        </p>
      </div>
    </body></html>
    """
    return subject, body


async def send_email(to: str, subject: str, html_body: str):
    """Send an HTML email via Minpay SMTP."""
    if not settings.smtp_pass:
        logger.warning("SMTP_PASS not set — skipping email")
        return

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.alert_email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_pass,
            start_tls=True,
        )
        logger.info(f"Email sent to {to}: {subject}")
    except Exception as e:
        logger.error(f"Email send failed: {e}")


class EmailService:
    def __init__(self, to_email: str):
        self.to = to_email or settings.alert_email_to

    async def trade_opened(self, symbol: str, signal: str, entry: float, confidence: float):
        if not self.to:
            return
        subject, body = _build_trade_email(
            "Trade Opened", symbol, signal, entry,
            reason=f"Claude confidence: {confidence:.0f}%"
        )
        await send_email(self.to, subject, body)

    async def trade_closed(self, symbol: str, signal: str, exit_price: float,
                           pnl: float, reason: str):
        if not self.to:
            return
        subject, body = _build_trade_email(
            "Trade Closed", symbol, signal, exit_price, pnl=pnl, reason=reason
        )
        await send_email(self.to, subject, body)

    async def daily_summary(self, metrics: dict):
        if not self.to:
            return
        pnl = metrics.get("total_pnl", 0)
        emoji = "🟢" if pnl >= 0 else "🔴"
        subject = f"[Trading Bot] {emoji} Daily Summary — ₹{pnl:,.2f}"
        trades = metrics.get("total_trades", 0)
        win_rate = metrics.get("win_rate", 0)
        body = f"""
        <html><body style="font-family: sans-serif; padding: 20px; background: #0f172a; color: #e2e8f0;">
          <div style="max-width: 500px; margin: auto; background: #1e293b; border-radius: 12px; padding: 24px;">
            <h2 style="color: #6366f1;">📈 Daily Trading Summary</h2>
            <p style="color: #94a3b8;">{datetime.now().strftime('%d %b %Y')}</p>
            <hr style="border-color: #334155;" />
            <table style="width: 100%;">
              <tr><td style="color: #94a3b8;">Total P&L</td>
                  <td style="text-align:right; font-weight:bold; font-size:1.2em; color:{'#22c55e' if pnl >= 0 else '#ef4444'};">
                    ₹{pnl:,.2f}</td></tr>
              <tr><td style="color: #94a3b8;">Total Trades</td><td style="text-align:right;">{trades}</td></tr>
              <tr><td style="color: #94a3b8;">Win Rate</td><td style="text-align:right;">{win_rate}%</td></tr>
              <tr><td style="color: #94a3b8;">Profit Factor</td><td style="text-align:right;">{metrics.get('profit_factor', 0):.2f}x</td></tr>
            </table>
          </div>
        </body></html>
        """
        await send_email(self.to, subject, body)

    async def bot_error(self, error_message: str):
        if not self.to:
            return
        subject = "[Trading Bot] ⚠️ Error Detected"
        body = f"""
        <html><body style="font-family:sans-serif;padding:20px;">
          <h3 style="color:#ef4444;">Bot Error</h3>
          <p>{error_message}</p>
          <p style="font-size:11px;color:#888;">LLM Trading Bot · {datetime.now().isoformat()}</p>
        </body></html>
        """
        await send_email(self.to, subject, body)
