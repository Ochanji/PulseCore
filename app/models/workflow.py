from datetime import datetime
from app.extensions import db


WORKFLOW_STATES = ['draft', 'submitted', 'under_review', 'approved', 'rejected', 'recalled']

WORKFLOW_TRANSITIONS = {
    'draft':        ['submitted'],
    'submitted':    ['under_review', 'approved', 'rejected'],
    'under_review': ['approved', 'rejected'],
    'approved':     ['recalled'],
    'rejected':     ['draft'],
    'recalled':     ['submitted'],
}


class WorkflowLog(db.Model):
    __tablename__ = 'workflow_logs'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)
    from_state = db.Column(db.String(32), nullable=True)
    to_state = db.Column(db.String(32), nullable=False)
    acted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    actor = db.relationship('User', foreign_keys=[acted_by])
    submission = db.relationship('FormSubmission', foreign_keys=[submission_id],
                                  backref=db.backref('workflow_logs', lazy='dynamic',
                                                      order_by='WorkflowLog.created_at'))

    __table_args__ = (
        db.Index('ix_wf_log_submission', 'submission_id'),
    )

    def __repr__(self):
        return f'<WorkflowLog {self.from_state} → {self.to_state}>'


def allowed_transitions(current_state):
    return WORKFLOW_TRANSITIONS.get(current_state, [])


STATE_LABELS = {
    'draft':        ('Draft',        'bg-gray-100 text-gray-600'),
    'submitted':    ('Submitted',    'bg-blue-100 text-blue-700'),
    'under_review': ('Under Review', 'bg-amber-100 text-amber-700'),
    'approved':     ('Approved',     'bg-green-100 text-green-700'),
    'rejected':     ('Rejected',     'bg-red-100 text-red-700'),
    'recalled':     ('Recalled',     'bg-purple-100 text-purple-700'),
}
