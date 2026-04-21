from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    USER_TYPES = ['web_user', 'mobile_worker']

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    user_type = db.Column(db.String(20), nullable=False, default='web_user')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_superadmin = db.Column(db.Boolean, default=False, nullable=False)
    primary_org_unit_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    unit_assignments = db.relationship('UserOrgUnit', backref='user', lazy='joined',
                                       foreign_keys='UserOrgUnit.user_id')
    primary_unit = db.relationship('OrgUnit', foreign_keys=[primary_org_unit_id])

    @property
    def full_name(self):
        parts = [self.first_name, self.last_name]
        return ' '.join(p for p in parts if p) or self.username

    def is_program_admin(self):
        from app.models.access import UserProgramAccess
        return UserProgramAccess.query.filter_by(
            user_id=self.id, role_in_program='manager', is_active=True
        ).count() > 0

    def get_managed_program_ids(self):
        from app.models.access import UserProgramAccess
        return [a.program_id for a in
                UserProgramAccess.query.filter_by(
                    user_id=self.id, role_in_program='manager', is_active=True
                ).all()]

    __table_args__ = (
        db.Index('ix_user_email', 'email'),
        db.Index('ix_user_org', 'org_id'),
    )

    def get_roles(self):
        roles = [a.role for a in self.unit_assignments]
        if self.is_superadmin:
            roles.append('superadmin')
        return roles

    def has_role(self, *roles):
        if self.is_superadmin:
            return True
        return any(r in roles for r in self.get_roles())

    def get_role_at_unit(self, org_unit_id):
        from app.utils.visibility import get_user_role_at_unit
        return get_user_role_at_unit(self.id, org_unit_id)

    def __repr__(self):
        return f'<User {self.email}>'


class UserOrgUnit(db.Model):
    __tablename__ = 'user_org_units'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    org_unit_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='data_entry')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'org_unit_id', name='uq_user_unit'),
        db.Index('ix_user_org_unit_user', 'user_id'),
    )

    ROLES = ['admin', 'supervisor', 'district_manager', 'data_entry', 'read_only', 'report_viewer']

    def __repr__(self):
        return f'<UserOrgUnit user={self.user_id} unit={self.org_unit_id} role={self.role}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
