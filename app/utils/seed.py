def seed_defaults():
    from app.models.organisation import Organisation
    from app.models.user import User
    from app.models.org_unit import OrgUnit, OrgUnitLevel
    from app.extensions import db
    import bcrypt

    if Organisation.query.first():
        return

    org = Organisation(name='Default Organisation', slug='default')
    db.session.add(org)
    db.session.flush()

    for level, name in [(0, 'Organisation'), (1, 'Region'), (2, 'District'), (3, 'Site')]:
        db.session.add(OrgUnitLevel(org_id=org.id, level=level, name=name))

    root = OrgUnit(org_id=org.id, parent_id=None, name='Default Organisation',
                   level=0, path='/', is_active=True)
    db.session.add(root)
    db.session.flush()
    root.path = f'/{root.id}/'

    pw = bcrypt.hashpw(b'Admin@PulseCore1', bcrypt.gensalt()).decode()
    admin = User(org_id=org.id, username='superadmin',
                 email='admin@pulsecore.local',
                 password_hash=pw, is_superadmin=True, is_active=True)
    db.session.add(admin)
    db.session.commit()
    print('PulseCore seeded. Login: admin@pulsecore.local / Admin@PulseCore1')
