from datetime import datetime
from app.extensions import db


class Form(db.Model):
    __tablename__ = 'forms'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entity_type = db.relationship('EntityType', backref='forms', foreign_keys=[entity_type_id])
    form_fields = db.relationship('FormField', backref='form', lazy='dynamic',
                                  order_by='FormField.order', cascade='all, delete-orphan')
    submissions = db.relationship('FormSubmission', backref='form', lazy='dynamic')

    __table_args__ = (
        db.Index('ix_form_org', 'org_id'),
        db.Index('ix_form_entity_type', 'entity_type_id'),
    )

    def __repr__(self):
        return f'<Form {self.name}>'


class FormField(db.Model):
    __tablename__ = 'form_fields'

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    entity_field_id = db.Column(db.Integer, db.ForeignKey('entity_fields.id'), nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    help_text = db.Column(db.Text, nullable=True)

    entity_field = db.relationship('EntityField', foreign_keys=[entity_field_id])

    __table_args__ = (
        db.UniqueConstraint('form_id', 'entity_field_id', name='uq_form_field'),
        db.Index('ix_form_field_form', 'form_id'),
    )

    def __repr__(self):
        return f'<FormField form={self.form_id} field={self.entity_field_id}>'


class FormSubmission(db.Model):
    __tablename__ = 'form_submissions'

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    record_id = db.Column(db.Integer, db.ForeignKey('records.id'), nullable=True)
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    org_unit_id = db.Column(db.Integer, db.ForeignKey('org_units.id'), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    raw_data = db.Column(db.Text, nullable=True)

    # Workflow
    workflow_state = db.Column(db.String(32), default='submitted', nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    record = db.relationship('Record', backref='submissions', foreign_keys=[record_id])
    submitter = db.relationship('User', foreign_keys=[submitted_by])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    org_unit = db.relationship('OrgUnit', foreign_keys=[org_unit_id])

    __table_args__ = (
        db.Index('ix_form_submission_form', 'form_id'),
        db.Index('ix_form_submission_record', 'record_id'),
        db.Index('ix_form_submission_state', 'workflow_state'),
    )

    def __repr__(self):
        return f'<FormSubmission form={self.form_id} record={self.record_id}>'
