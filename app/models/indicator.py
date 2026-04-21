from datetime import datetime
from app.extensions import db


AGGREGATION_TYPES = ['sum', 'count', 'average', 'max', 'min']

TARGET_TYPES = ['cumulative', 'monthly', 'quarterly', 'annual']


class Indicator(db.Model):
    __tablename__ = 'indicators'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(64), nullable=True)
    description = db.Column(db.Text, nullable=True)
    unit = db.Column(db.String(64), nullable=True)           # e.g. "individuals", "sessions", "%"
    sector = db.Column(db.String(64), nullable=True)
    aggregation = db.Column(db.String(32), default='sum', nullable=False)
    target_type = db.Column(db.String(32), default='cumulative', nullable=False)

    # Link to entity field that drives this indicator's value
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=True)
    entity_field_id = db.Column(db.Integer, db.ForeignKey('entity_fields.id'), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    program = db.relationship('Program', foreign_keys=[program_id],
                               backref=db.backref('indicators', lazy='dynamic'))
    entity_type = db.relationship('EntityType', foreign_keys=[entity_type_id])
    entity_field = db.relationship('EntityField', foreign_keys=[entity_field_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    targets = db.relationship('IndicatorTarget', backref='indicator', lazy='dynamic',
                               cascade='all, delete-orphan')
    values = db.relationship('IndicatorValue', backref='indicator', lazy='dynamic',
                              cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('ix_indicator_org', 'org_id'),
        db.Index('ix_indicator_program', 'program_id'),
    )

    def __repr__(self):
        return f'<Indicator {self.code} {self.name}>'


class IndicatorTarget(db.Model):
    __tablename__ = 'indicator_targets'

    id = db.Column(db.Integer, primary_key=True)
    indicator_id = db.Column(db.Integer, db.ForeignKey('indicators.id'), nullable=False)
    org_unit_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=True)
    period_year = db.Column(db.Integer, nullable=False)
    period_month = db.Column(db.Integer, nullable=True)   # None = annual target
    target_value = db.Column(db.Float, nullable=False)

    org_unit = db.relationship('OrgUnit', foreign_keys=[org_unit_id])

    __table_args__ = (
        db.UniqueConstraint('indicator_id', 'org_unit_id', 'period_year', 'period_month',
                            name='uq_indicator_target'),
        db.Index('ix_ind_target_indicator', 'indicator_id'),
    )

    def __repr__(self):
        return f'<IndicatorTarget ind={self.indicator_id} {self.period_year}/{self.period_month}>'


class IndicatorValue(db.Model):
    __tablename__ = 'indicator_values'

    id = db.Column(db.Integer, primary_key=True)
    indicator_id = db.Column(db.Integer, db.ForeignKey('indicators.id'), nullable=False)
    org_unit_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=True)
    period_year = db.Column(db.Integer, nullable=False)
    period_month = db.Column(db.Integer, nullable=False)
    value = db.Column(db.Float, nullable=False, default=0)
    is_manual = db.Column(db.Boolean, default=False, nullable=False)  # manual override vs computed
    computed_at = db.Column(db.DateTime, nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    org_unit = db.relationship('OrgUnit', foreign_keys=[org_unit_id])
    updater = db.relationship('User', foreign_keys=[updated_by])

    __table_args__ = (
        db.UniqueConstraint('indicator_id', 'org_unit_id', 'period_year', 'period_month',
                            name='uq_indicator_value'),
        db.Index('ix_ind_value_indicator', 'indicator_id'),
    )

    def __repr__(self):
        return f'<IndicatorValue ind={self.indicator_id} {self.period_year}/{self.period_month} = {self.value}>'
