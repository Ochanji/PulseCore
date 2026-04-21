from datetime import datetime
from app.extensions import db


class Household(db.Model):
    __tablename__ = 'households'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    org_unit_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=True)
    household_code = db.Column(db.String(64), nullable=True)
    head_name = db.Column(db.String(255), nullable=True)
    address = db.Column(db.Text, nullable=True)
    gps_lat = db.Column(db.Float, nullable=True)
    gps_lng = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    org_unit = db.relationship('OrgUnit', foreign_keys=[org_unit_id])
    members = db.relationship('Participant', backref='household', lazy='dynamic')

    __table_args__ = (
        db.Index('ix_household_org', 'org_id'),
        db.Index('ix_household_org_unit', 'org_unit_id'),
    )

    def __repr__(self):
        return f'<Household {self.household_code}>'


CONSENT_STATUSES = ['pending', 'given', 'withdrawn', 'expired']

GENDERS = ['male', 'female', 'other', 'prefer_not_to_say']


class Participant(db.Model):
    __tablename__ = 'participants'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    org_unit_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=True)
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Identity
    first_name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(32), nullable=True)
    national_id = db.Column(db.String(128), nullable=True)
    phone = db.Column(db.String(32), nullable=True)
    case_number = db.Column(db.String(64), nullable=True, unique=True)

    # Consent
    consent_status = db.Column(db.String(32), default='pending', nullable=False)
    consent_date = db.Column(db.Date, nullable=True)
    consent_expiry = db.Column(db.Date, nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    org_unit = db.relationship('OrgUnit', foreign_keys=[org_unit_id])
    registrar = db.relationship('User', foreign_keys=[registered_by])
    enrollments = db.relationship('ProgramEnrollment', backref='participant', lazy='dynamic',
                                   cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('ix_participant_org', 'org_id'),
        db.Index('ix_participant_org_unit', 'org_unit_id'),
        db.Index('ix_participant_national_id', 'national_id'),
        db.Index('ix_participant_case_number', 'case_number'),
    )

    @property
    def full_name(self):
        parts = [self.first_name]
        if self.last_name:
            parts.append(self.last_name)
        return ' '.join(parts)

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = datetime.utcnow().date()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def __repr__(self):
        return f'<Participant {self.full_name}>'


class ProgramEnrollment(db.Model):
    __tablename__ = 'program_enrollments'

    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    org_unit_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=True)
    enrolled_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    exited_at = db.Column(db.DateTime, nullable=True)
    exit_reason = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(32), default='active', nullable=False)  # active, exited, transferred
    notes = db.Column(db.Text, nullable=True)

    program = db.relationship('Program', foreign_keys=[program_id])
    org_unit = db.relationship('OrgUnit', foreign_keys=[org_unit_id])
    enrolled_by_user = db.relationship('User', foreign_keys=[enrolled_by])

    __table_args__ = (
        db.UniqueConstraint('participant_id', 'program_id', name='uq_participant_program'),
        db.Index('ix_enrollment_participant', 'participant_id'),
        db.Index('ix_enrollment_program', 'program_id'),
    )

    def __repr__(self):
        return f'<ProgramEnrollment participant={self.participant_id} program={self.program_id}>'
