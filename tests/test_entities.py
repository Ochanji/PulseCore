import pytest
from app import create_app
from app.extensions import db
from app.models.organisation import Organisation
from app.models.entity import EntityType, EntityField
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
def client(app):
    return app.test_client()


@pytest.fixture
def org(app):
    with app.app_context():
        org = Organisation(name='Test Org', slug='test')
        db.session.add(org)
        db.session.commit()
        return org


def test_create_entity_type(app, org):
    with app.app_context():
        org = Organisation.query.first()
        et = EntityType(
            org_id=org.id,
            name='Beneficiary',
            slug='beneficiary',
            is_lookup=False,
        )
        db.session.add(et)
        db.session.commit()

        assert EntityType.query.count() == 1
        assert EntityType.query.first().name == 'Beneficiary'


def test_entity_type_slug_unique_per_org(app, org):
    with app.app_context():
        org = Organisation.query.first()
        et1 = EntityType(org_id=org.id, name='A', slug='same')
        et2 = EntityType(org_id=org.id, name='B', slug='same')
        db.session.add(et1)
        db.session.commit()
        db.session.add(et2)
        with pytest.raises(Exception):
            db.session.commit()


def test_entity_field_types(app, org):
    with app.app_context():
        org = Organisation.query.first()
        et = EntityType(org_id=org.id, name='Visit', slug='visit')
        db.session.add(et)
        db.session.flush()

        for ft, _ in EntityField.FIELD_TYPES:
            f = EntityField(
                entity_type_id=et.id,
                name=f'field_{ft}',
                label=ft.title(),
                field_type=ft,
                order=0,
            )
            db.session.add(f)

        db.session.commit()
        assert EntityField.query.count() == len(EntityField.FIELD_TYPES)


def test_entity_field_options(app, org):
    with app.app_context():
        org = Organisation.query.first()
        et = EntityType(org_id=org.id, name='Case', slug='case')
        db.session.add(et)
        db.session.flush()

        f = EntityField(
            entity_type_id=et.id,
            name='status',
            label='Status',
            field_type='select',
            order=0,
        )
        f.set_options_list(['Active', 'Closed', 'Pending'])
        db.session.add(f)
        db.session.commit()

        loaded = EntityField.query.first()
        assert loaded.get_options_list() == ['Active', 'Closed', 'Pending']


def test_parent_entity_type(app, org):
    with app.app_context():
        org = Organisation.query.first()
        parent = EntityType(org_id=org.id, name='Beneficiary', slug='beneficiary')
        db.session.add(parent)
        db.session.flush()

        child = EntityType(
            org_id=org.id,
            name='Visit',
            slug='visit',
            parent_entity_type_id=parent.id,
        )
        db.session.add(child)
        db.session.commit()

        loaded = EntityType.query.filter_by(slug='visit').first()
        assert loaded.parent_entity_type_id == parent.id
