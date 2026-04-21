from datetime import datetime
from app.extensions import db


PROGRAM_ROLES = ['viewer', 'data_entry', 'reviewer', 'manager']


class UserProgramAccess(db.Model):
    __tablename__ = 'user_program_access'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    role_in_program = db.Column(db.String(32), default='data_entry', nullable=False)
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship('User', foreign_keys=[user_id],
                            backref=db.backref('program_access', lazy='dynamic'))
    program = db.relationship('Program', foreign_keys=[program_id],
                               backref=db.backref('user_access', lazy='dynamic'))
    grantor = db.relationship('User', foreign_keys=[granted_by])

    __table_args__ = (
        db.UniqueConstraint('user_id', 'program_id', name='uq_user_program'),
        db.Index('ix_upa_user', 'user_id'),
        db.Index('ix_upa_program', 'program_id'),
    )

    def __repr__(self):
        return f'<UserProgramAccess user={self.user_id} program={self.program_id}>'


class UserApplicationAccess(db.Model):
    __tablename__ = 'user_application_access'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    can_submit = db.Column(db.Boolean, default=True, nullable=False)
    can_view = db.Column(db.Boolean, default=True, nullable=False)
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship('User', foreign_keys=[user_id],
                            backref=db.backref('application_access', lazy='dynamic'))
    application = db.relationship('Application', foreign_keys=[application_id],
                                   backref=db.backref('user_access', lazy='dynamic'))
    grantor = db.relationship('User', foreign_keys=[granted_by])

    __table_args__ = (
        db.UniqueConstraint('user_id', 'application_id', name='uq_user_application'),
        db.Index('ix_uaa_user', 'user_id'),
        db.Index('ix_uaa_application', 'application_id'),
    )

    def __repr__(self):
        return f'<UserApplicationAccess user={self.user_id} app={self.application_id}>'
