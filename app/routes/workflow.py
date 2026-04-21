from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.form import FormSubmission
from app.models.workflow import WorkflowLog, allowed_transitions, STATE_LABELS
from app.utils.visibility import visible_unit_ids
from datetime import datetime

workflow_bp = Blueprint('workflow', __name__, url_prefix='/workflow')


def _require_access():
    from app.utils.role_access import can_access
    if not current_user.is_superadmin and not can_access('workflow'):
        flash('Access denied.', 'error')
        return False
    return True


@workflow_bp.route('/')
@login_required
def queue():
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    unit_ids = visible_unit_ids(current_user.id)
    state_filter = request.args.get('state', 'submitted')

    q = FormSubmission.query.filter(
        FormSubmission.org_unit_id.in_(unit_ids),
        FormSubmission.workflow_state == state_filter,
    ).order_by(FormSubmission.submitted_at.desc())

    submissions = q.limit(100).all()
    counts = {}
    for s in ['submitted', 'under_review', 'approved', 'rejected']:
        counts[s] = FormSubmission.query.filter(
            FormSubmission.org_unit_id.in_(unit_ids),
            FormSubmission.workflow_state == s,
        ).count()

    return render_template(
        'workflow/queue.html',
        submissions=submissions,
        counts=counts,
        state_filter=state_filter,
        state_labels=STATE_LABELS,
    )


@workflow_bp.route('/<int:submission_id>')
@login_required
def review(submission_id):
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    sub = FormSubmission.query.get_or_404(submission_id)
    logs = sub.workflow_logs.order_by(WorkflowLog.created_at.asc()).all()
    transitions = allowed_transitions(sub.workflow_state)

    import json
    raw = {}
    if sub.raw_data:
        try:
            raw = json.loads(sub.raw_data)
        except Exception:
            pass

    return render_template(
        'workflow/review.html',
        submission=sub,
        logs=logs,
        transitions=transitions,
        raw_data=raw,
        state_labels=STATE_LABELS,
    )


@workflow_bp.route('/<int:submission_id>/transition', methods=['POST'])
@login_required
def transition(submission_id):
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    sub = FormSubmission.query.get_or_404(submission_id)
    new_state = request.form.get('new_state')
    comment = request.form.get('comment', '').strip() or None

    if new_state not in allowed_transitions(sub.workflow_state):
        flash('Invalid workflow transition.', 'error')
        return redirect(url_for('workflow.review', submission_id=sub.id))

    log = WorkflowLog(
        submission_id=sub.id,
        from_state=sub.workflow_state,
        to_state=new_state,
        acted_by=current_user.id,
        comment=comment,
    )
    db.session.add(log)

    sub.workflow_state = new_state
    if new_state in ('approved', 'rejected'):
        sub.reviewed_by = current_user.id
        sub.reviewed_at = datetime.utcnow()

    db.session.commit()
    flash(f'Submission moved to {STATE_LABELS[new_state][0]}.', 'success')
    return redirect(url_for('workflow.queue'))
