from datetime import datetime
from app.extensions import db


class Organisation(db.Model):
    __tablename__ = 'organisations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    org_units = db.relationship('OrgUnit', backref='organisation', lazy='dynamic')
    users = db.relationship('User', backref='organisation', lazy='dynamic')
    entity_types = db.relationship('EntityType', backref='organisation', lazy='dynamic')
    forms = db.relationship('Form', backref='organisation', lazy='dynamic')

    def __repr__(self):
        return f'<Organisation {self.name}>'
