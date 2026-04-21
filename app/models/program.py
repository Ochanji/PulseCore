from datetime import datetime
from app.extensions import db


SECTORS = [
    'health', 'nutrition', 'wash', 'shelter', 'education',
    'livelihoods', 'protection', 'gbv', 'child_protection',
    'food_security', 'cccm', 'early_recovery', 'other',
]


class Program(db.Model):
    __tablename__ = 'programs'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(64), nullable=True)
    sector = db.Column(db.String(64), nullable=True)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by])
    grants = db.relationship('Grant', backref='program', lazy='dynamic',
                              cascade='all, delete-orphan')
    enrollments = db.relationship('ProgramEnrollment', backref='program_ref',
                                   lazy='dynamic', foreign_keys='ProgramEnrollment.program_id')

    __table_args__ = (
        db.Index('ix_program_org', 'org_id'),
    )

    @property
    def total_budget(self):
        return sum(g.budget or 0 for g in self.grants if g.is_active)

    @property
    def active_participants(self):
        from app.models.participant import ProgramEnrollment
        return ProgramEnrollment.query.filter_by(
            program_id=self.id, status='active'
        ).count()

    def __repr__(self):
        return f'<Program {self.name}>'


class Grant(db.Model):
    __tablename__ = 'grants'

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    grant_code = db.Column(db.String(128), nullable=True)
    donor = db.Column(db.String(255), nullable=True)
    budget = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(8), default='USD', nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('ix_grant_program', 'program_id'),
        db.Index('ix_grant_org', 'org_id'),
    )

    @property
    def is_expired(self):
        if not self.end_date:
            return False
        return self.end_date < datetime.utcnow().date()

    def __repr__(self):
        return f'<Grant {self.grant_code} / {self.donor}>'
