from datetime import datetime
from app.extensions import db


class ReportingEntity(db.Model):
    __tablename__ = 'reporting_entities'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    org_unit_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=True)
    grant_id = db.Column(db.Integer, db.ForeignKey('grants.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    org_unit = db.relationship('OrgUnit', foreign_keys=[org_unit_id])
    grant = db.relationship('Grant', foreign_keys=[grant_id])
    creator = db.relationship('User', foreign_keys=[created_by])

    app_links = db.relationship('ReportingEntityApp', backref='reporting_entity',
                                 cascade='all, delete-orphan', lazy='dynamic')
    user_links = db.relationship('ReportingEntityUser', backref='reporting_entity',
                                  cascade='all, delete-orphan', lazy='dynamic')

    __table_args__ = (
        db.Index('ix_re_org', 'org_id'),
        db.UniqueConstraint('org_id', 'code', name='uq_re_code'),
    )

    def get_users(self):
        from app.models.user import User
        ids = [l.user_id for l in self.user_links]
        return User.query.filter(User.id.in_(ids)).all() if ids else []

    def get_applications(self):
        from app.models.application import Application
        ids = [l.application_id for l in self.app_links]
        return Application.query.filter(Application.id.in_(ids)).all() if ids else []

    def __repr__(self):
        return f'<ReportingEntity {self.code}>'


class ReportingEntityApp(db.Model):
    __tablename__ = 'reporting_entity_apps'

    id = db.Column(db.Integer, primary_key=True)
    reporting_entity_id = db.Column(db.Integer, db.ForeignKey('reporting_entities.id'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)

    application = db.relationship('Application', foreign_keys=[application_id])

    __table_args__ = (
        db.UniqueConstraint('reporting_entity_id', 'application_id', name='uq_re_app'),
    )


class ReportingEntityUser(db.Model):
    __tablename__ = 'reporting_entity_users'

    id = db.Column(db.Integer, primary_key=True)
    reporting_entity_id = db.Column(db.Integer, db.ForeignKey('reporting_entities.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User', foreign_keys=[user_id])

    __table_args__ = (
        db.UniqueConstraint('reporting_entity_id', 'user_id', name='uq_re_user'),
    )
