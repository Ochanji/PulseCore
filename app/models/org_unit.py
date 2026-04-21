from datetime import datetime
from app.extensions import db


class OrgUnitLevel(db.Model):
    __tablename__ = 'org_unit_levels'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('org_id', 'level', name='uq_org_level'),
    )

    def __repr__(self):
        return f'<OrgUnitLevel {self.level}:{self.name}>'


class OrgUnit(db.Model):
    __tablename__ = 'org_units'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), nullable=True)
    level = db.Column(db.Integer, nullable=False, default=0)
    path = db.Column(db.String(500), nullable=False, default='/')
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    children = db.relationship('OrgUnit', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    user_assignments = db.relationship('UserOrgUnit', backref='org_unit', lazy='dynamic')

    __table_args__ = (
        db.Index('ix_org_unit_path', 'path'),
        db.Index('ix_org_unit_org', 'org_id'),
    )

    def get_level_name(self):
        level_obj = OrgUnitLevel.query.filter_by(org_id=self.org_id, level=self.level).first()
        return level_obj.name if level_obj else f'Level {self.level}'

    def get_ancestors(self):
        if not self.path:
            return []
        ids = [int(x) for x in self.path.strip('/').split('/') if x]
        ids = [i for i in ids if i != self.id]
        return OrgUnit.query.filter(OrgUnit.id.in_(ids)).all() if ids else []

    def __repr__(self):
        return f'<OrgUnit {self.name}>'
