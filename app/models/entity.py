from datetime import datetime
from app.extensions import db


class EntityType(db.Model):
    __tablename__ = 'entity_types'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(10), nullable=True)
    is_lookup = db.Column(db.Boolean, default=False, nullable=False)
    form_mode = db.Column(db.String(10), default='create', nullable=False)  # 'create' | 'update'
    parent_entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fields = db.relationship('EntityField', backref='entity_type', lazy='dynamic',
                             order_by='EntityField.order',
                             foreign_keys='EntityField.entity_type_id')
    child_entity_types = db.relationship('EntityType', backref=db.backref('parent_entity_type', remote_side=[id]),
                                         lazy='dynamic', foreign_keys=[parent_entity_type_id])

    __table_args__ = (
        db.UniqueConstraint('org_id', 'slug', name='uq_entity_type_slug'),
        db.Index('ix_entity_type_org', 'org_id'),
    )

    def get_list_fields(self):
        return self.fields.filter_by(display_in_list=True).order_by(EntityField.order).all()

    def __repr__(self):
        return f'<EntityType {self.name}>'


class EntityField(db.Model):
    __tablename__ = 'entity_fields'

    FIELD_TYPES = [
        ('text',         'Text'),
        ('textarea',     'Long Text'),
        ('integer',      'Integer'),
        ('decimal',      'Decimal'),
        ('phone',        'Phone / Numeric ID'),
        ('date',         'Date'),
        ('time',         'Time'),
        ('datetime',     'Date & Time'),
        ('select',       'Single Select'),
        ('multi_select', 'Checkbox (Multi-select)'),
        ('boolean',      'Yes / No'),
        ('photo',        'Photo'),
        ('file',         'File Upload'),
        ('gps',          'GPS Location'),
        ('lookup',       'Lookup Table'),
        ('label',        'Label / Instruction'),
        ('hidden',       'Hidden Value'),
        ('barcode',      'Barcode / QR Code'),
        ('rating',       'Rating'),
        ('group',        'Group'),
        ('repeat_group', 'Repeat Group'),
    ]

    FIELD_CATEGORIES = [
        ('Text',      'T',  [('text','Text'),('textarea','Long Text')]),
        ('Multiple Choice', '=', [('select','Single Select'),('multi_select','Checkbox (Multi-select)')]),
        ('Number',    '1',  [('integer','Integer'),('decimal','Decimal'),('phone','Phone / Numeric ID')]),
        ('Date',      'cal',[('date','Date'),('time','Time'),('datetime','Date & Time')]),
        ('Media',     'cam',[('photo','Photo'),('file','File Upload')]),
        ('Location',  'pin',[('gps','GPS Location'),('barcode','Barcode / QR Code')]),
        ('Special',   '...',[('boolean','Yes / No'),('rating','Rating'),('label','Label'),('hidden','Hidden Value')]),
        ('Lookup',    'lnk',[('lookup','Lookup Table')]),
        ('Groups',    'grp',[('group','Group'),('repeat_group','Repeat Group')]),
    ]

    id = db.Column(db.Integer, primary_key=True)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(255), nullable=False)
    field_type = db.Column(db.String(30), nullable=False, default='text')
    is_required = db.Column(db.Boolean, default=False, nullable=False)
    is_unique = db.Column(db.Boolean, default=False, nullable=False)
    options = db.Column(db.Text, nullable=True)
    lookup_entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=True)
    display_in_list = db.Column(db.Boolean, default=False, nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)

    lookup_source = db.Column(db.String(20), nullable=True, default='entity')  # 'entity'|'org_unit'|'user'
    default_value = db.Column(db.String(500), nullable=True)
    display_condition = db.Column(db.Text, nullable=True)   # JSON: {"field":"x","op":"==","value":"y"}
    calculated_formula = db.Column(db.String(500), nullable=True)  # e.g. "{doses_admin} + {doses_wasted}"

    lookup_entity_type = db.relationship('EntityType', foreign_keys=[lookup_entity_type_id])

    __table_args__ = (
        db.UniqueConstraint('entity_type_id', 'name', name='uq_entity_field_name'),
        db.Index('ix_entity_field_entity_type', 'entity_type_id'),
    )

    def get_options_list(self):
        if not self.options:
            return []
        import json
        try:
            return json.loads(self.options)
        except Exception:
            return []

    def set_options_list(self, options_list):
        import json
        self.options = json.dumps(options_list)

    def __repr__(self):
        return f'<EntityField {self.name}:{self.field_type}>'
