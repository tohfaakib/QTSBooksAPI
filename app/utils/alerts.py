import os, smtplib, ssl
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from typing import Tuple

def build_change_summary(db, since_hours: int = 24) -> dict:
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)

    total = db["changes"].count_documents({"changed_at": {"$gte": since}})
    new_count = db["changes"].count_documents({
        "changed_at": {"$gte": since}, "change_kind": "new"
    })
    updated_count = db["changes"].count_documents({
        "changed_at": {"$gte": since}, "change_kind": "update"
    })
    significant_count = db["changes"].count_documents({
        "changed_at": {"$gte": since}, "significant": True
    })

    sample = []
    for doc in db["changes"].find(
        {"changed_at": {"$gte": since}, "significant": True}
    ).sort("changed_at", -1).limit(10):
        fields = ", ".join(list(doc.get("fields_changed", {}).keys())[:3])
        sample.append({"url": doc.get("url"), "fields": fields, "at": doc.get("changed_at")})

    return {
        "since": since.isoformat(),
        "total": total,
        "new": new_count,
        "updated": updated_count,
        "significant": significant_count,
        "significant_sample": sample,
    }

def _format_summary_text(summary: dict) -> str:
    lines = [
        f"Change Summary (since {summary['since']})",
        f"- Total changes: {summary['total']}",
        f"- New items:     {summary['new']}",
        f"- Updates:       {summary['updated']}",
        f"- Significant:   {summary['significant']}",
    ]
    if summary["significant_sample"]:
        lines.append("\nRecent significant changes:")
        for s in summary["significant_sample"]:
            when = s["at"].strftime("%Y-%m-%d %H:%M:%S %Z") if hasattr(s["at"], "strftime") else str(s["at"])
            lines.append(f"  • {s['url']}  [{s['fields']}]  at {when}")
    return "\n".join(lines)

def send_email_alert(subject: str, body: str) -> Tuple[bool, str]:
    smtp_host = os.getenv("ALERT_SMTP_HOST")
    smtp_port = int(os.getenv("ALERT_SMTP_PORT", "587"))
    smtp_user = os.getenv("ALERT_SMTP_USER")
    smtp_pass = os.getenv("ALERT_SMTP_PASS")
    mail_from = os.getenv("ALERT_FROM")
    mail_to = os.getenv("ALERT_TO")

    if not all([smtp_host, smtp_user, smtp_pass, mail_from, mail_to]):
        return False, "Email not configured (set ALERT_* envs)."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=context)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

    return True, f"Email sent to {mail_to}"
