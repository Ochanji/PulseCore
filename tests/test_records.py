import pytest
from app import create_app
from app.extensions import db
from app.models.organisation import Organisation
from app.models.entity import EntityType, EntityField
from app.models.record import Record, RecordValue, RecordLink
from app.models.org_unit import OrgUnit
from app.models.user import User


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def setup(app):
    with app.app_context():
        org = Organisation(name='Test Org', slug='test')
        db.session.add(org)
        db.session.flush()

        unit = OrgUnit(org_id=org.id, name='HQ', level=0, path='/', is_active=True)
        db.session.add(unit)
        db.session.flush()
        unit.path = f'/{unit.id}/'

        user = User(org_id=org.id, username='admin', email='a@b.com',
                    password_hash='x', is_active=True, is_superadmin=True)
        db.session.add(user)
        db.session.flush()

        et = EntityType(org_id=org.id, name='Beneficiary', slug='beneficiary')
        db.session.add(et)
        db.session.flush()

        name_field = EntityField(
            entity_type_id=et.id, name='full_name', label='Full Name',
            field_type='text', is_required=True, display_in_list=True, order=0
        )
        db.session.add(name_field)
        db.session.commit()
        return {'org': org, 'unit': unit, 'user': user, 'et': et, 'field': name_field}


def test_create_record(app, setup):
    with app.app_context():
        s = {k: db.session.merge(v) for k, v in setup.items()}
        record = Record(
            org_id=s['org'].id,
            entity_type_id=s['et'].id,
            org_unit_id=s['unit'].id,
            created_by=s['user'].id,
            display_label='Test Record',
        )
        db.session.add(record)
        db.session.flush()

        rv = RecordValue(record_id=record.id, entity_field_id=s['field'].id,
                         value_text='Jane Doe')
        db.session.add(rv)
        record.compute_display_label()
        db.session.commit()

        loaded = Record.query.first()
        assert loaded.display_label == 'Jane Doe'
        assert loaded.get_value(s['field'].id) == 'Jane Doe'


def test_record_link(app, setup):
    with app.app_context():
        s = {k: db.session.merge(v) for k, v in setup.items()}
        r1 = Record(org_id=s['org'].id, entity_type_id=s['et'].id,
                    org_unit_id=s['unit'].id, display_label='R1')
        r2 = Record(org_id=s['org'].id, entity_type_id=s['et'].id,
                    org_unit_id=s['unit'].id, display_label='R2')
        db.session.add_all([r1, r2])
        db.session.flush()

        link = RecordLink(source_record_id=r1.id, target_record_id=r2.id)
        db.session.add(link)
        db.session.commit()

        assert RecordLink.query.count() == 1
        assert RecordLink.query.first().source_record_id == r1.id


def test_parent_child_records(app, setup):
    with app.app_context():
        s = {k: db.session.merge(v) for k, v in setup.items()}
        parent = Record(org_id=s['org'].id, entity_type_id=s['et'].id,
                        org_unit_id=s['unit'].id, display_label='Parent')
        db.session.add(parent)
        db.session.flush()

        child = Record(org_id=s['org'].id, entity_type_id=s['et'].id,
                       org_unit_id=s['unit'].id, parent_record_id=parent.id,
                       display_label='Child')
        db.session.add(child)
        db.session.commit()

        assert child.parent_record_id == parent.id
        assert parent.children.count() == 1
