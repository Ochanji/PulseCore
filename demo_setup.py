"""
GAVI REACH Kenya — Demo Data Setup
Clears all data (except users/org), builds Kenya immunisation structure,
floods with 6 months of vaccine dose records, assigns specific users.
"""
import random
from datetime import datetime, date, timedelta
from app import create_app
from app.extensions import db, bcrypt
from sqlalchemy import text

app = create_app()

VACCINES = [
    ('BCG',             'Bacille Calmette-Guérin (TB)',           1.0),
    ('OPV-0',           'Oral Polio Vaccine (Birth dose)',         0.95),
    ('OPV-1',           'Oral Polio Vaccine (6 weeks)',            0.85),
    ('OPV-2',           'Oral Polio Vaccine (10 weeks)',           0.82),
    ('OPV-3',           'Oral Polio Vaccine (14 weeks)',           0.78),
    ('DPT-HepB-Hib-1',  'Pentavalent Dose 1 (6 weeks)',           0.85),
    ('DPT-HepB-Hib-2',  'Pentavalent Dose 2 (10 weeks)',          0.82),
    ('DPT-HepB-Hib-3',  'Pentavalent Dose 3 (14 weeks)',          0.78),
    ('PCV-1',           'Pneumococcal Dose 1',                    0.84),
    ('PCV-2',           'Pneumococcal Dose 2',                    0.80),
    ('PCV-3',           'Pneumococcal Dose 3',                    0.76),
    ('Rotavirus-1',     'Rotavirus Dose 1',                       0.83),
    ('Rotavirus-2',     'Rotavirus Dose 2',                       0.79),
    ('IPV',             'Inactivated Polio Vaccine (14 weeks)',    0.77),
    ('MR-1',            'Measles-Rubella Dose 1 (9 months)',       0.65),
    ('MR-2',            'Measles-Rubella Dose 2 (18 months)',      0.48),
    ('Yellow-Fever',    'Yellow Fever (9 months)',                 0.62),
    ('HPV-1',           'HPV Dose 1 (girls 10+)',                 0.38),
    ('HPV-2',           'HPV Dose 2 (girls 10+)',                 0.33),
    ('TT',              'Tetanus Toxoid (pregnant women)',         0.50),
]

NAIROBI_FACILITIES = [
    ('Kenyatta National Hospital',  'KNH-001',  380),
    ('Pumwani Maternity Hospital',  'PMH-001',  260),
    ('Mathare Health Centre',       'MHC-001',  140),
    ('Kangemi Health Centre',       'KGM-001',  105),
]

ELDORET_FACILITIES = [
    ('Moi Teaching & Referral Hospital', 'MTRH-001', 310),
    ('Eldoret West Health Centre',       'EWH-001',  155),
    ('Langas Health Centre',             'LHC-001',  100),
    ('Huruma Health Facility',           'HHF-001',   75),
]

NAIROBI_WORKERS  = ['Nurse Wanjiku Kamau', 'CHW Otieno Omondi', 'Nurse Achieng Adhiambo', 'Dr. Muthoni Kariuki']
ELDORET_WORKERS  = ['Nurse Chebet Ruto', 'CHW Kibet Sang', 'Nurse Jepleting Koech', 'Dr. Kemboi Mutai']

REPORT_MONTHS = [
    date(2024, 11, 30),
    date(2024, 12, 31),
    date(2025,  1, 31),
    date(2025,  2, 28),
    date(2025,  3, 31),
    date(2025,  4, 30),
]


def clear_data(conn):
    tables = [
        'record_values', 'records',
        'form_submissions', 'form_fields', 'forms',
        'reporting_entity_users', 'reporting_entity_apps', 'reporting_entities',
        'app_entity_types', 'app_forms', 'applications',
        'entity_fields', 'entity_types',
        'program_enrollments', 'participants', 'households',
        'indicator_values', 'indicator_targets', 'indicators',
        'user_application_access', 'user_program_access', 'user_org_units',
        'workflow_logs', 'audit_logs',
        'grants', 'programs',
        'org_unit_levels', 'org_units',
    ]
    for t in tables:
        try:
            conn.execute(text(f'DELETE FROM {t}'))
        except Exception:
            pass
    conn.commit()
    print('  Data cleared.')


def ensure_user(org_id, email, username, full_name, password='GaviReach2024!'):
    from app.models.user import User
    u = User.query.filter_by(email=email).first()
    if not u:
        first, *rest = full_name.split()
        u = User(
            org_id=org_id,
            username=username,
            email=email,
            first_name=first,
            last_name=' '.join(rest) if rest else None,
            user_type='web_user',
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            is_active=True,
        )
        db.session.add(u)
        db.session.flush()
        print(f'  Created user: {email}')
    else:
        print(f'  Found user:   {email}')
    return u


def run():
    with app.app_context():
        from app.models.organisation import Organisation
        from app.models.org_unit import OrgUnit, OrgUnitLevel
        from app.models.program import Program, Grant
        from app.models.application import Application, AppEntityType
        from app.models.entity import EntityType, EntityField
        from app.models.record import Record, RecordValue
        from app.models.user import User, UserOrgUnit
        from app.models.reporting_entity import ReportingEntity, ReportingEntityApp, ReportingEntityUser

        db.create_all()

        # ── Clear data ────────────────────────────────────────────────────────
        print('\n[1] Clearing data …')
        with db.engine.connect() as conn:
            clear_data(conn)

        org = Organisation.query.first()
        if not org:
            print('No organisation found. Run the app first to seed defaults.')
            return

        superadmin = User.query.filter_by(is_superadmin=True).first()
        sa_id = superadmin.id if superadmin else None

        # ── Org structure ─────────────────────────────────────────────────────
        print('\n[2] Building Kenya org structure …')

        lvl0 = OrgUnitLevel(org_id=org.id, level=0, name='Country')
        lvl1 = OrgUnitLevel(org_id=org.id, level=1, name='County')
        lvl2 = OrgUnitLevel(org_id=org.id, level=2, name='Health Facility')
        db.session.add_all([lvl0, lvl1, lvl2])
        db.session.flush()

        kenya = OrgUnit(org_id=org.id, name='Kenya', code='KE', level=0, path='/', is_active=True)
        db.session.add(kenya)
        db.session.flush()
        kenya.path = f'/{kenya.id}/'

        nairobi = OrgUnit(org_id=org.id, name='Nairobi County', code='NBI',
                          level=1, parent_id=kenya.id, path=kenya.path, is_active=True)
        db.session.add(nairobi)
        db.session.flush()
        nairobi.path = f'{kenya.path}{nairobi.id}/'

        eldoret = OrgUnit(org_id=org.id, name='Uasin Gishu County', code='UGC',
                          level=1, parent_id=kenya.id, path=kenya.path, is_active=True)
        db.session.add(eldoret)
        db.session.flush()
        eldoret.path = f'{kenya.path}{eldoret.id}/'

        nairobi_units, eldoret_units = {}, {}

        for name, code, _ in NAIROBI_FACILITIES:
            u = OrgUnit(org_id=org.id, name=name, code=code, level=2,
                        parent_id=nairobi.id, path=nairobi.path, is_active=True)
            db.session.add(u)
            db.session.flush()
            u.path = f'{nairobi.path}{u.id}/'
            nairobi_units[code] = u

        for name, code, _ in ELDORET_FACILITIES:
            u = OrgUnit(org_id=org.id, name=name, code=code, level=2,
                        parent_id=eldoret.id, path=eldoret.path, is_active=True)
            db.session.add(u)
            db.session.flush()
            u.path = f'{eldoret.path}{u.id}/'
            eldoret_units[code] = u

        db.session.flush()
        print('  Org units created.')

        # ── Program & Grant ───────────────────────────────────────────────────
        print('\n[3] Creating GAVI REACH program & grant …')

        program = Program(
            org_id=org.id,
            name='GAVI REACH Kenya',
            sector='health',
            description='Reaching Every Child with life-saving vaccines across Kenya counties.',
            start_date=date(2024, 1, 1),
            end_date=date(2026, 12, 31),
            is_active=True,
            created_by=sa_id,
        )
        db.session.add(program)
        db.session.flush()

        grant = Grant(
            program_id=program.id,
            org_id=org.id,
            name='GAVI REACH 2024-2026',
            donor='Gavi, the Vaccine Alliance',
            grant_code='GAVI-KE-2024-001',
            budget=2_500_000.00,
            currency='USD',
            start_date=date(2024, 1, 1),
            end_date=date(2026, 12, 31),
            is_active=True,
        )
        db.session.add(grant)
        db.session.flush()
        print('  Program and grant created.')

        # ── Application ───────────────────────────────────────────────────────
        print('\n[4] Creating Vaccine Dose Monitor application …')

        vac_app = Application(
            org_id=org.id,
            name='Vaccine Dose Monitor',
            description='Track daily immunisation doses per vaccine across health facilities.',
            icon='💉',
            color='blue',
            created_by=sa_id,
            is_active=True,
        )
        db.session.add(vac_app)
        db.session.flush()

        # ── Entity Type & Fields ──────────────────────────────────────────────
        et = EntityType(
            org_id=org.id,
            created_by=sa_id,
            name='Vaccine Administration Record',
            slug='vaccine_administration_record',
            description='Monthly immunisation doses administered per vaccine per facility.',
            icon='💉',
            is_active=True,
        )
        db.session.add(et)
        db.session.flush()

        db.session.add(AppEntityType(application_id=vac_app.id, entity_type_id=et.id))

        field_defs = [
            ('reporting_date',       'Reporting Date',         'date',   True,  True),
            ('facility_name',        'Health Facility',        'text',   True,  True),
            ('facility_code',        'Facility Code',          'text',   True,  True),
            ('county',               'County',                 'select', True,  True),
            ('vaccine',              'Vaccine',                'select', True,  True),
            ('doses_administered',   'Doses Administered',     'number', True,  True),
            ('doses_wasted',         'Doses Wasted',           'number', False, False),
            ('stock_balance',        'Closing Stock Balance',  'number', False, False),
            ('health_worker',        'Reported By',            'text',   False, True),
            ('notes',                'Notes',                  'text',   False, False),
        ]
        county_opts  = ['Nairobi', 'Uasin Gishu']
        vaccine_opts = [v[0] for v in VACCINES]

        fields_map = {}
        for idx, (name, label, ftype, required, display) in enumerate(field_defs):
            f = EntityField(
                entity_type_id=et.id,
                created_by=sa_id,
                name=name,
                label=label,
                field_type=ftype,
                is_required=required,
                display_in_list=display,
                order=idx,
            )
            if name == 'county':
                f.set_options_list(county_opts)
            if name == 'vaccine':
                f.set_options_list(vaccine_opts)
            db.session.add(f)
            db.session.flush()
            fields_map[name] = f

        db.session.flush()
        print('  Application, entity type, and fields created.')

        # ── Users ─────────────────────────────────────────────────────────────
        print('\n[5] Ensuring users exist …')
        vmercell  = ensure_user(org.id, 'vmercell@gmail.com',   'vmercell',  'Victor Mercell')
        vochanji  = ensure_user(org.id, 'vochanji@hotmail.com', 'vochanji',  'V Ochanji')

        # Assign org units
        db.session.add(UserOrgUnit(user_id=vmercell.id,  org_unit_id=nairobi.id, role='data_entry'))
        db.session.add(UserOrgUnit(user_id=vochanji.id,  org_unit_id=eldoret.id, role='data_entry'))
        db.session.flush()

        # ── Reporting Entities ────────────────────────────────────────────────
        print('\n[6] Creating Reporting Entities …')

        re_nairobi = ReportingEntity(
            org_id=org.id,
            name='GAVI REACH — Nairobi County',
            code='GAVI-KE-NBI-2024',
            description='GAVI REACH immunisation reporting entity for Nairobi County facilities.',
            org_unit_id=nairobi.id,
            grant_id=grant.id,
            is_active=True,
            created_by=sa_id,
        )
        re_eldoret = ReportingEntity(
            org_id=org.id,
            name='GAVI REACH — Uasin Gishu County',
            code='GAVI-KE-UGC-2024',
            description='GAVI REACH immunisation reporting entity for Uasin Gishu (Eldoret) facilities.',
            org_unit_id=eldoret.id,
            grant_id=grant.id,
            is_active=True,
            created_by=sa_id,
        )
        db.session.add_all([re_nairobi, re_eldoret])
        db.session.flush()

        db.session.add(ReportingEntityApp(reporting_entity_id=re_nairobi.id, application_id=vac_app.id))
        db.session.add(ReportingEntityApp(reporting_entity_id=re_eldoret.id, application_id=vac_app.id))
        db.session.add(ReportingEntityUser(reporting_entity_id=re_nairobi.id, user_id=vmercell.id))
        db.session.add(ReportingEntityUser(reporting_entity_id=re_eldoret.id, user_id=vochanji.id))
        db.session.flush()
        print('  Nairobi RE -> vmercell@gmail.com')
        print('  Eldoret RE -> vochanji@hotmail.com')

        # ── Flood Records ─────────────────────────────────────────────────────
        print('\n[7] Generating vaccine dose records …')

        def make_records(facilities, county_name, county_unit, workers, user, re_id):
            count = 0
            for fname, fcode, base_doses in facilities:
                funit = (nairobi_units if county_name == 'Nairobi' else eldoret_units)[fcode]
                for rpt_date in REPORT_MONTHS:
                    for vname, vdesc, ratio in VACCINES:
                        variance  = random.uniform(0.82, 1.18)
                        doses_adm = max(1, round(base_doses * ratio * variance))
                        wasted    = max(0, round(doses_adm * random.uniform(0.01, 0.05)))
                        stock     = max(0, round(doses_adm * random.uniform(1.1, 1.5)))
                        worker    = random.choice(workers)

                        rec = Record(
                            org_id=org.id,
                            entity_type_id=et.id,
                            org_unit_id=funit.id,
                            created_by=user.id,
                            created_at=rpt_date,
                            is_active=True,
                            program_id=program.id,
                            grant_id=grant.id,
                            display_label=f'{fname} / {vname} / {rpt_date.strftime("%b %Y")}',
                        )
                        db.session.add(rec)
                        db.session.flush()

                        vals = [
                            (fields_map['reporting_date'],     rpt_date.isoformat(), None),
                            (fields_map['facility_name'],      fname,                None),
                            (fields_map['facility_code'],      fcode,                None),
                            (fields_map['county'],             county_name,          None),
                            (fields_map['vaccine'],            vname,                None),
                            (fields_map['doses_administered'], None,                 doses_adm),
                            (fields_map['doses_wasted'],       None,                 wasted),
                            (fields_map['stock_balance'],      None,                 stock),
                            (fields_map['health_worker'],      worker,               None),
                        ]
                        for field, vtext, vnum in vals:
                            db.session.add(RecordValue(
                                record_id=rec.id,
                                entity_field_id=field.id,
                                value_text=vtext,
                                value_number=vnum,
                            ))
                        count += 1
            return count

        n_nairobi = make_records(NAIROBI_FACILITIES, 'Nairobi',      nairobi, NAIROBI_WORKERS, vmercell, re_nairobi.id)
        n_eldoret = make_records(ELDORET_FACILITIES, 'Uasin Gishu',  eldoret, ELDORET_WORKERS, vochanji, re_eldoret.id)

        db.session.commit()

        total = n_nairobi + n_eldoret
        print(f'  Nairobi  records: {n_nairobi}')
        print(f'  Eldoret  records: {n_eldoret}')
        print(f'  Total records:    {total}')

        # ── Migration: add reporting_entity_id to records ─────────────────────
        with db.engine.connect() as conn:
            try:
                conn.execute(text(
                    'ALTER TABLE records ADD COLUMN reporting_entity_id INTEGER REFERENCES reporting_entities(id)'
                ))
                conn.commit()
            except Exception:
                pass

        print('\n[OK] GAVI REACH Kenya demo setup complete.')
        print(f'\n  Credentials:')
        print(f'  Superadmin  -> admin@pulsecore.local  / Admin1234!')
        print(f'  Nairobi     -> vmercell@gmail.com     / GaviReach2024!')
        print(f'  Eldoret     -> vochanji@hotmail.com   / GaviReach2024!')


if __name__ == '__main__':
    run()
