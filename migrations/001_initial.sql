-- PulseCore initial schema (reference only — db.create_all() handles this in dev)
-- Use this as a reference for MySQL production migrations.

CREATE TABLE IF NOT EXISTS organisations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS org_unit_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    level INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    UNIQUE (org_id, level)
);

CREATE TABLE IF NOT EXISTS org_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    parent_id INTEGER REFERENCES org_units(id),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    level INTEGER NOT NULL DEFAULT 0,
    path VARCHAR(500) NOT NULL DEFAULT '/',
    is_active BOOLEAN NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    is_superadmin BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_org_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    org_unit_id INTEGER NOT NULL REFERENCES org_units(id),
    role VARCHAR(20) NOT NULL DEFAULT 'data_entry',
    UNIQUE (user_id, org_unit_id)
);

CREATE TABLE IF NOT EXISTS entity_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    created_by INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(10),
    is_lookup BOOLEAN NOT NULL DEFAULT 0,
    parent_entity_type_id INTEGER REFERENCES entity_types(id),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (org_id, slug)
);

CREATE TABLE IF NOT EXISTS entity_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type_id INTEGER NOT NULL REFERENCES entity_types(id),
    created_by INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    label VARCHAR(255) NOT NULL,
    field_type VARCHAR(30) NOT NULL DEFAULT 'text',
    is_required BOOLEAN NOT NULL DEFAULT 0,
    is_unique BOOLEAN NOT NULL DEFAULT 0,
    options TEXT,
    lookup_entity_type_id INTEGER REFERENCES entity_types(id),
    display_in_list BOOLEAN NOT NULL DEFAULT 0,
    "order" INTEGER NOT NULL DEFAULT 0,
    UNIQUE (entity_type_id, name)
);

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    entity_type_id INTEGER NOT NULL REFERENCES entity_types(id),
    org_unit_id INTEGER NOT NULL REFERENCES org_units(id),
    parent_record_id INTEGER REFERENCES records(id),
    created_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    display_label VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS record_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL REFERENCES records(id),
    entity_field_id INTEGER NOT NULL REFERENCES entity_fields(id),
    value_text TEXT,
    value_number REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (record_id, entity_field_id)
);

CREATE TABLE IF NOT EXISTS record_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_record_id INTEGER NOT NULL REFERENCES records(id),
    target_record_id INTEGER NOT NULL REFERENCES records(id),
    entity_field_id INTEGER REFERENCES entity_fields(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    created_by INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    entity_type_id INTEGER NOT NULL REFERENCES entity_types(id),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    version INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS form_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id INTEGER NOT NULL REFERENCES forms(id),
    entity_field_id INTEGER NOT NULL REFERENCES entity_fields(id),
    "order" INTEGER NOT NULL DEFAULT 0,
    is_visible BOOLEAN NOT NULL DEFAULT 1,
    help_text TEXT,
    UNIQUE (form_id, entity_field_id)
);

CREATE TABLE IF NOT EXISTS form_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id INTEGER NOT NULL REFERENCES forms(id),
    record_id INTEGER REFERENCES records(id),
    submitted_by INTEGER REFERENCES users(id),
    org_unit_id INTEGER REFERENCES org_units(id),
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    raw_data TEXT
);
