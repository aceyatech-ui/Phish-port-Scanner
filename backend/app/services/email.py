from flask import current_app
from flask_mail import Mail, Message
import os
from weasyprint import HTML
import tempfile

mail = Mail()

def init_mail(app):
    mail.init_app(app)

def send_pdf_report(recipient_email, scan, report_html):
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            HTML(string=report_html).write_pdf(tmp.name)
            tmp_path = tmp.name

        subject = f"RECON Security Report: {scan.target}"
        body = f"""
Hello,

Your security assessment for {scan.target} is complete.

Please find the attached PDF report.

Scan Date: {scan.completed_at or scan.created_at}
Security Score: {scan.results.get('score', 'N/A')}/100

Thank you for using RECON.

---
RECON Security Platform
"""

        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=body,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )

        with open(tmp_path, 'rb') as f:
            msg.attach(
                f"recon-report-{scan.target}-{scan.id[:8]}.pdf",
                'application/pdf',
                f.read()
            )

        mail.send(msg)
        os.unlink(tmp_path)
        return True, "PDF sent successfully"

    except Exception as e:
        current_app.logger.error(f"Failed to send PDF email: {str(e)}")
        return False, str(e)