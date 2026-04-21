from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import extract, func
from datetime import datetime, timedelta
from app.models.entity import EntityType
from app.models.record import Record
from app.models.form import Form, FormSubmission
from app.models.application import Application
from app.models.participant import Participant
from app.models.program import Program
from app.utils.visibility import visible_unit_ids
from app.utils.role_access import is_data_entry_only, is_report_viewer_only
from app.extensions import db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    if is_data_entry_only():
        return redirect(url_for('applications.index'))
    if is_report_viewer_only():
        return redirect(url_for('reports.index'))

    unit_ids = visible_unit_ids(current_user.id)
    org_id = current_user.org_id
    now = datetime.utcnow()

    entity_types = EntityType.query.filter_by(org_id=org_id, is_active=True).all()

    # Summary counts
    total_records = Record.query.filter(
        Record.org_id == org_id,
        Record.org_unit_id.in_(unit_ids),
        Record.is_active == True,
    ).count()

    total_participants = Participant.query.filter(
        Participant.org_id == org_id,
        Participant.is_active == True,
    ).count()

    total_programs = Program.query.filter_by(org_id=org_id, is_active=True).count()

    pending_approvals = FormSubmission.query.filter(
        FormSubmission.org_unit_id.in_(unit_ids),
        FormSubmission.workflow_state == 'submitted',
    ).count()

    # Records per entity type
    stats = {}
    for et in entity_types:
        stats[et.id] = Record.query.filter(
            Record.entity_type_id == et.id,
            Record.org_unit_id.in_(unit_ids),
            Record.is_active == True,
        ).count()

    # Submissions last 12 months for chart
    monthly_submissions = []
    for i in range(11, -1, -1):
        month_dt = (now.replace(day=1) - timedelta(days=i * 28))
        y, m = month_dt.year, month_dt.month
        count = db.session.query(func.count(FormSubmission.id)).filter(
            FormSubmission.org_unit_id.in_(unit_ids),
            extract('year', FormSubmission.submitted_at) == y,
            extract('month', FormSubmission.submitted_at) == m,
        ).scalar() or 0
        monthly_submissions.append({'label': month_dt.strftime('%b %y'), 'count': count})

    # Recent submissions
    recent_submissions = FormSubmission.query.filter(
        FormSubmission.org_unit_id.in_(unit_ids),
    ).order_by(FormSubmission.submitted_at.desc()).limit(8).all()

    installed_apps = Application.query.filter_by(
        org_id=org_id, is_active=True
    ).order_by(Application.name).all()

    return render_template(
        'dashboard/index.html',
        entity_types=entity_types,
        stats=stats,
        installed_apps=installed_apps,
        total_records=total_records,
        total_participants=total_participants,
        total_programs=total_programs,
        pending_approvals=pending_approvals,
        monthly_submissions=monthly_submissions,
        recent_submissions=recent_submissions,
    )
