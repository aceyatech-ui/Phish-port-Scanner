from app.models import db, Scan
from app.services.recon import run_recon
from datetime import datetime

def perform_scan(scan_id):
    scan = Scan.query.get(scan_id)
    if not scan:
        return
    try:
        scan.status = 'running'
        scan.started_at = datetime.utcnow()
        db.session.commit()

        results = run_recon(scan.target)

        scan.results = results
        scan.status = 'completed'
        scan.completed_at = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        scan.status = 'failed'
        scan.error_message = str(e)
        db.session.commit()