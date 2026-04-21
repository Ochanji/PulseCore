from datetime import datetime
from app.extensions import db


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organisations.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(10), nullable=True)
    color = db.Column(db.String(20), nullable=True, default='blue')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    template_key = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    entity_type_links = db.relationship('AppEntityType', backref='application',
                                         lazy='dynamic', cascade='all, delete-orphan')
    form_links = db.relationship('AppForm', backref='application',
                                  lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by])

    __table_args__ = (
        db.Index('ix_application_org', 'org_id'),
    )

    def get_entity_types(self):
        from app.models.entity import EntityType
        ids = [l.entity_type_id for l in self.entity_type_links]
        if not ids:
            return []
        return EntityType.query.filter(
            EntityType.id.in_(ids), EntityType.is_active == True
        ).order_by(EntityType.name).all()

    def get_forms(self):
        from app.models.form import Form
        ids = [l.form_id for l in self.form_links]
        if not ids:
            return []
        return Form.query.filter(
            Form.id.in_(ids), Form.is_active == True
        ).order_by(Form.name).all()

    def color_classes(self):
        mapping = {
            'blue':   ('bg-blue-50',   'text-blue-700',   'border-blue-200',  'bg-blue-600'),
            'red':    ('bg-red-50',    'text-red-700',    'border-red-200',   'bg-red-600'),
            'green':  ('bg-green-50',  'text-green-700',  'border-green-200', 'bg-green-600'),
            'purple': ('bg-purple-50', 'text-purple-700', 'border-purple-200','bg-purple-600'),
            'amber':  ('bg-amber-50',  'text-amber-700',  'border-amber-200', 'bg-amber-600'),
            'teal':   ('bg-teal-50',   'text-teal-700',   'border-teal-200',  'bg-teal-600'),
        }
        return mapping.get(self.color or 'blue', mapping['blue'])

    def __repr__(self):
        return f'<Application {self.name}>'


class AppEntityType(db.Model):
    __tablename__ = 'app_entity_types'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=False)

    entity_type = db.relationship('EntityType', foreign_keys=[entity_type_id])

    __table_args__ = (
        db.UniqueConstraint('application_id', 'entity_type_id', name='uq_app_entity_type'),
    )


class AppForm(db.Model):
    __tablename__ = 'app_forms'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)

    form = db.relationship('Form', foreign_keys=[form_id])

    __table_args__ = (
        db.UniqueConstraint('application_id', 'form_id', name='uq_app_form'),
    )
