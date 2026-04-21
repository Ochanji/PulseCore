from app import create_app
from app.extensions import db

app = create_app()


def _migrate_columns():
    """Add new columns to existing tables without dropping data."""
    from sqlalchemy import text
    migrations = [
        # records table — IRC-scale linkages
        "ALTER TABLE records ADD COLUMN participant_id INTEGER REFERENCES participants(id)",
        "ALTER TABLE records ADD COLUMN program_id INTEGER REFERENCES programs(id)",
        "ALTER TABLE records ADD COLUMN grant_id INTEGER REFERENCES grants(id)",
        # form_submissions table — workflow
        "ALTER TABLE form_submissions ADD COLUMN workflow_state VARCHAR(32) DEFAULT 'submitted'",
        "ALTER TABLE form_submissions ADD COLUMN reviewed_by INTEGER REFERENCES users(id)",
        "ALTER TABLE form_submissions ADD COLUMN reviewed_at DATETIME",
        # users table — extended profile + type
        "ALTER TABLE users ADD COLUMN first_name VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN last_name VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN phone VARCHAR(50)",
        "ALTER TABLE users ADD COLUMN user_type VARCHAR(20) DEFAULT 'web_user'",
        "ALTER TABLE users ADD COLUMN primary_org_unit_id INTEGER REFERENCES org_units(id)",
        # entity_types — form mode
        "ALTER TABLE entity_types ADD COLUMN form_mode VARCHAR(10) DEFAULT 'create'",
        # entity_fields — logic layer
        "ALTER TABLE entity_fields ADD COLUMN lookup_source VARCHAR(20) DEFAULT 'entity'",
        "ALTER TABLE entity_fields ADD COLUMN default_value VARCHAR(500)",
        "ALTER TABLE entity_fields ADD COLUMN display_condition TEXT",
        "ALTER TABLE entity_fields ADD COLUMN calculated_formula VARCHAR(500)",
    ]
    with db.engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # column already exists — safe to skip


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        _migrate_columns()
        from app.utils.seed import seed_defaults
        seed_defaults()
    app.run(debug=True, host='0.0.0.0', port=5000)
