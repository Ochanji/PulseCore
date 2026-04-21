from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(64), nullable=False)     # create, update, delete, login, export
    resource_type = db.Column(db.String(64), nullable=True)  # Record, Participant, FormSubmission
    resource_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.Text, nullable=True)            # JSON diff or description
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    actor = db.relationship('User', foreign_keys=[user_id])

    __table_args__ = (
        db.Index('ix_audit_org', 'org_id'),
        db.Index('ix_audit_user', 'user_id'),
        db.Index('ix_audit_resource', 'resource_type', 'resource_id'),
        db.Index('ix_audit_created', 'created_at'),
    )

    def __repr__(self):
        return f'<AuditLog {self.action} {self.resource_type}#{self.resource_id}>'


def log_action(action, resource_type=None, resource_id=None, detail=None):
    """Helper — call from routes to write an audit entry."""
    from flask import request
    from flask_login import current_user
    try:
        org_id = current_user.org_id if current_user.is_authenticated else None
        user_id = current_user.id if current_user.is_authenticated else None
        ip = request.remote_addr
    except Exception:
        org_id = user_id = ip = None

    entry = AuditLog(
        org_id=org_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip,
    )
    db.session.add(entry)
