import pytest
from app import create_app
from app.extensions import db
from app.models.organisation import Organisation
from app.models.org_unit import OrgUnit
from app.models.user import User, UserOrgUnit
from app.utils.visibility import visible_unit_ids, get_user_role_at_unit


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def hierarchy(app):
    with app.app_context():
        org = Organisation(name='Test', slug='test')
        db.session.add(org)
        db.session.flush()

        root = OrgUnit(org_id=org.id, name='Country', level=0, path='/', is_active=True)
        db.session.add(root)
        db.session.flush()
        root.path = f'/{root.id}/'

        region = OrgUnit(org_id=org.id, parent_id=root.id, name='North', level=1,
                         path=f'/{root.id}/', is_active=True)
        db.session.add(region)
        db.session.flush()
        region.path = f'/{root.id}/{region.id}/'

        site = OrgUnit(org_id=org.id, parent_id=region.id, name='Clinic A', level=2,
                       path=f'/{root.id}/{region.id}/', is_active=True)
        db.session.add(site)
        db.session.flush()
        site.path = f'/{root.id}/{region.id}/{site.id}/'

        user = User(org_id=org.id, username='u', email='u@test.com',
                    password_hash='x', is_active=True)
        db.session.add(user)
        db.session.flush()

        db.session.add(UserOrgUnit(user_id=user.id, org_unit_id=region.id, role='supervisor'))
        db.session.commit()

        return {'org': org, 'root': root, 'region': region, 'site': site, 'user': user}


def test_visible_unit_ids_cascades_down(app, hierarchy):
    with app.app_context():
        h = {k: db.session.merge(v) for k, v in hierarchy.items()}
        ids = visible_unit_ids(h['user'].id)
        # Assigned to region — should see region + site below it, not root above
        assert h['region'].id in ids
        assert h['site'].id in ids
        assert h['root'].id not in ids


def test_role_at_assigned_unit(app, hierarchy):
    with app.app_context():
        h = {k: db.session.merge(v) for k, v in hierarchy.items()}
        role = get_user_role_at_unit(h['user'].id, h['region'].id)
        assert role == 'supervisor'


def test_role_at_child_unit_inherits(app, hierarchy):
    with app.app_context():
        h = {k: db.session.merge(v) for k, v in hierarchy.items()}
        role = get_user_role_at_unit(h['user'].id, h['site'].id)
        assert role == 'supervisor'


def test_no_role_at_unrelated_unit(app, hierarchy):
    with app.app_context():
        h = {k: db.session.merge(v) for k, v in hierarchy.items()}
        role = get_user_role_at_unit(h['user'].id, h['root'].id)
        assert role is None
