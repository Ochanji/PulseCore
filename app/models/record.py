from datetime import datetime
from app.extensions import db


class Record(db.Model):
    __tablename__ = 'records'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=False)
    org_unit_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=False)
    parent_record_id = db.Column(db.Integer, db.ForeignKey('records.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    display_label = db.Column(db.String(500), nullable=True)

    # IRC-scale linkages
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=True)
    grant_id = db.Column(db.Integer, db.ForeignKey('grants.id'), nullable=True)

    entity_type = db.relationship('EntityType', backref='records', foreign_keys=[entity_type_id])
    org_unit = db.relationship('OrgUnit', backref='records', foreign_keys=[org_unit_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    participant = db.relationship('Participant', foreign_keys=[participant_id],
                                   backref=db.backref('records', lazy='dynamic'))
    program = db.relationship('Program', foreign_keys=[program_id])
    grant = db.relationship('Grant', foreign_keys=[grant_id])
    values = db.relationship('RecordValue', backref='record', lazy='dynamic',
                             cascade='all, delete-orphan')
    children = db.relationship('Record', backref=db.backref('parent', remote_side=[id]),
                                lazy='dynamic', foreign_keys=[parent_record_id])
    outgoing_links = db.relationship('RecordLink', foreign_keys='RecordLink.source_record_id',
                                     backref='source_record', lazy='dynamic',
                                     cascade='all, delete-orphan')
    incoming_links = db.relationship('RecordLink', foreign_keys='RecordLink.target_record_id',
                                     backref='target_record', lazy='dynamic')

    __table_args__ = (
        db.Index('ix_record_entity_type', 'entity_type_id'),
        db.Index('ix_record_org_unit', 'org_unit_id'),
        db.Index('ix_record_org', 'org_id'),
        db.Index('ix_record_updated', 'updated_at'),
        db.Index('ix_record_participant', 'participant_id'),
        db.Index('ix_record_program', 'program_id'),
    )

    def get_value(self, field_id):
        rv = self.values.filter_by(entity_field_id=field_id).first()
        return rv.value_text if rv else None

    def compute_display_label(self):
        from app.models.entity import EntityField
        list_fields = EntityField.query.filter_by(
            entity_type_id=self.entity_type_id, display_in_list=True
        ).order_by(EntityField.order).all()
        parts = []
        for f in list_fields:
            val = self.get_value(f.id)
            if val:
                parts.append(val)
        if parts:
            self.display_label = ' / '.join(parts)
        else:
            self.display_label = f'Record #{self.id}'

    def __repr__(self):
        return f'<Record {self.id} {self.display_label}>'


class RecordValue(db.Model):
    __tablename__ = 'record_values'

    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('records.id'), nullable=False)
    entity_field_id = db.Column(db.Integer, db.ForeignKey('entity_fields.id'), nullable=False)
    value_text = db.Column(db.Text, nullable=True)
    value_number = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entity_field = db.relationship('EntityField', foreign_keys=[entity_field_id])

    __table_args__ = (
        db.UniqueConstraint('record_id', 'entity_field_id', name='uq_record_field'),
        db.Index('ix_record_value_record', 'record_id'),
    )

    def __repr__(self):
        return f'<RecordValue field={self.entity_field_id} value={self.value_text}>'


class RecordLink(db.Model):
    __tablename__ = 'record_links'

    id = db.Column(db.Integer, primary_key=True)
    source_record_id = db.Column(db.Integer, db.ForeignKey('records.id'), nullable=False)
    target_record_id = db.Column(db.Integer, db.ForeignKey('records.id'), nullable=False)
    entity_field_id = db.Column(db.Integer, db.ForeignKey('entity_fields.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    entity_field = db.relationship('EntityField', foreign_keys=[entity_field_id])

    __table_args__ = (
        db.Index('ix_record_link_source', 'source_record_id'),
        db.Index('ix_record_link_target', 'target_record_id'),
    )

    def __repr__(self):
        return f'<RecordLink {self.source_record_id} → {self.target_record_id}>'
