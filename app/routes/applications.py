from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.application import Application, AppEntityType, AppForm
from app.models.entity import EntityType, EntityField
from app.models.form import Form, FormField
from app.utils.decorators import require_role
from app.utils.role_access import can_access

applications_bp = Blueprint('applications', __name__, url_prefix='/apps')


# ── Helpers ───────────────────────────────────────────────────────────────────

def install_from_template(template_key, org_id, user_id):
    from app.app_registry import get_template

    defn = get_template(template_key)
    if not defn:
        return None, 'Template not found.'

    existing = Application.query.filter_by(org_id=org_id, template_key=template_key).first()
    if existing:
        return existing, 'Already installed.'

    app_record = Application(
        org_id=org_id,
        name=defn['name'],
        description=defn['description'],
        icon=defn['icon'],
        color=defn.get('color', 'blue'),
        template_key=template_key,
        created_by=user_id,
    )
    db.session.add(app_record)
    db.session.flush()

    slug_to_et = {}

    for et_def in defn['entity_types']:
        et = EntityType.query.filter_by(org_id=org_id, slug=et_def['slug']).first()
        if not et:
            et = EntityType(
                org_id=org_id,
                created_by=user_id,
                name=et_def['name'],
                slug=et_def['slug'],
                description=et_def.get('description', ''),
                icon=et_def.get('icon', ''),
                is_lookup=et_def.get('is_lookup', False),
                is_active=True,
            )
            db.session.add(et)
            db.session.flush()

            for idx, fd in enumerate(et_def.get('fields', [])):
                f = EntityField(
                    entity_type_id=et.id,
                    created_by=user_id,
                    name=fd['name'],
                    label=fd['label'],
                    field_type=fd['field_type'],
                    is_required=fd.get('is_required', False),
                    display_in_list=fd.get('display_in_list', False),
                    order=idx,
                )
                if 'options' in fd:
                    f.set_options_list(fd['options'])
                db.session.add(f)
                db.session.flush()
                # store lookup_slug for later resolution
                if 'lookup_slug' in fd:
                    f._lookup_slug = fd['lookup_slug']

        slug_to_et[et_def['slug']] = et
        if not AppEntityType.query.filter_by(application_id=app_record.id, entity_type_id=et.id).first():
            db.session.add(AppEntityType(application_id=app_record.id, entity_type_id=et.id))

    # Resolve parent + lookup relationships
    for et_def in defn['entity_types']:
        et = slug_to_et[et_def['slug']]
        if et_def.get('parent_slug') and et_def['parent_slug'] in slug_to_et:
            et.parent_entity_type_id = slug_to_et[et_def['parent_slug']].id
        for field in et.fields.all():
            if hasattr(field, '_lookup_slug') and field._lookup_slug:
                target = slug_to_et.get(field._lookup_slug)
                if target:
                    field.lookup_entity_type_id = target.id

    # Create forms
    for form_def in defn.get('forms', []):
        et = slug_to_et.get(form_def['entity_type_slug'])
        if not et:
            continue
        form = Form(
            org_id=org_id,
            created_by=user_id,
            name=form_def['name'],
            description=form_def.get('description', ''),
            entity_type_id=et.id,
            is_active=True,
        )
        db.session.add(form)
        db.session.flush()
        for idx, field_name in enumerate(form_def.get('fields', [])):
            field = EntityField.query.filter_by(
                entity_type_id=et.id, name=field_name
            ).first()
            if field:
                db.session.add(FormField(
                    form_id=form.id,
                    entity_field_id=field.id,
                    order=idx,
                    is_visible=True,
                ))
        if not AppForm.query.filter_by(application_id=app_record.id, form_id=form.id).first():
            db.session.add(AppForm(application_id=app_record.id, form_id=form.id))

    db.session.commit()
    return app_record, None


# ── Routes ────────────────────────────────────────────────────────────────────

@applications_bp.route('/')
@login_required
def index():
    from app.utils.visibility import visible_app_ids
    app_ids = visible_app_ids(current_user)
    apps = Application.query.filter(
        Application.org_id == current_user.org_id,
        Application.is_active == True,
        Application.id.in_(app_ids),
    ).order_by(Application.name).all()
    return render_template('applications/index.html', apps=apps)


@applications_bp.route('/manage')
@login_required
@require_role('admin')
def manage():
    apps = Application.query.filter_by(
        org_id=current_user.org_id, is_active=True
    ).order_by(Application.name).all()
    return render_template('applications/manage.html', apps=apps)


@applications_bp.route('/manage/new', methods=['POST'])
@login_required
@require_role('admin')
def new_app():
    name = request.form.get('name', '').strip()
    if not name:
        flash('App name is required.', 'error')
        return redirect(url_for('applications.manage'))

    app_record = Application(
        org_id=current_user.org_id,
        created_by=current_user.id,
        name=name,
        description=request.form.get('description', ''),
        icon=request.form.get('icon', '📦'),
        color=request.form.get('color', 'blue'),
    )
    db.session.add(app_record)
    db.session.commit()
    flash(f'Application "{name}" created.', 'success')
    return redirect(url_for('applications.builder', app_id=app_record.id))


@applications_bp.route('/<int:app_id>/edit', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def edit_app(app_id):
    app_record = Application.query.filter_by(
        id=app_id, org_id=current_user.org_id
    ).first_or_404()

    if request.method == 'POST':
        app_record.name = request.form.get('name', app_record.name).strip()
        app_record.description = request.form.get('description', '')
        app_record.icon = request.form.get('icon', app_record.icon)
        app_record.color = request.form.get('color', app_record.color)
        db.session.commit()
        flash('Application updated.', 'success')
        return redirect(url_for('applications.builder', app_id=app_record.id))

    return render_template('applications/manage.html',
                           apps=Application.query.filter_by(org_id=current_user.org_id, is_active=True).all(),
                           edit_app=app_record)


@applications_bp.route('/<int:app_id>/builder', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def builder(app_id):
    app_record = Application.query.filter_by(
        id=app_id, org_id=current_user.org_id
    ).first_or_404()

    all_entity_types = EntityType.query.filter_by(
        org_id=current_user.org_id, is_active=True
    ).order_by(EntityType.name).all()
    all_forms = Form.query.filter_by(
        org_id=current_user.org_id, is_active=True
    ).order_by(Form.name).all()

    if request.method == 'POST':
        # Update entity type links
        AppEntityType.query.filter_by(application_id=app_record.id).delete()
        for et_id in request.form.getlist('entity_type_ids'):
            db.session.add(AppEntityType(
                application_id=app_record.id,
                entity_type_id=int(et_id),
            ))

        # Update form links
        AppForm.query.filter_by(application_id=app_record.id).delete()
        for form_id in request.form.getlist('form_ids'):
            db.session.add(AppForm(
                application_id=app_record.id,
                form_id=int(form_id),
            ))

        db.session.commit()
        flash('Application configuration saved.', 'success')
        return redirect(url_for('applications.builder', app_id=app_record.id))

    linked_ets = app_record.get_entity_types()
    linked_forms = app_record.get_forms()

    # Serialize entity fields for JS
    import json as _json
    et_fields_map = {}
    for et in linked_ets:
        et_fields_map[et.id] = {
            'name': et.name,
            'icon': et.icon or '',
            'description': et.description or '',
            'is_lookup': et.is_lookup,
            'form_mode': et.form_mode or 'create',
            'fields': [
                {
                    'id': f.id,
                    'name': f.name,
                    'label': f.label,
                    'field_type': f.field_type,
                    'is_required': f.is_required,
                    'is_unique': f.is_unique,
                    'display_in_list': f.display_in_list,
                    'options': f.get_options_list(),
                    'lookup_entity_type_id': f.lookup_entity_type_id,
                    'lookup_source': f.lookup_source or 'entity',
                    'default_value': f.default_value or '',
                    'display_condition': f.display_condition or '',
                    'calculated_formula': f.calculated_formula or '',
                }
                for f in et.fields.order_by(EntityField.order).all()
            ]
        }

    active_panel = request.args.get('panel', '')

    from app.models.org_unit import OrgUnit
    org_units = OrgUnit.query.filter_by(
        org_id=current_user.org_id, is_active=True
    ).order_by(OrgUnit.path).all()

    return render_template('applications/builder.html',
                           app=app_record,
                           linked_ets=linked_ets,
                           linked_forms=linked_forms,
                           all_entity_types=all_entity_types,
                           org_units=org_units,
                           field_types=EntityField.FIELD_TYPES,
                           et_fields_map_json=_json.dumps(et_fields_map),
                           active_panel=active_panel)


@applications_bp.route('/<int:app_id>/add-entity', methods=['POST'])
@login_required
@require_role('admin')
def add_entity(app_id):
    import re
    app_record = Application.query.filter_by(
        id=app_id, org_id=current_user.org_id
    ).first_or_404()

    name = request.form.get('name', '').strip()
    if not name:
        flash('Data type name is required.', 'error')
        return redirect(url_for('applications.builder', app_id=app_id))

    def slugify(t):
        t = t.lower().strip()
        t = re.sub(r'[^\w\s-]', '', t)
        return re.sub(r'[\s_-]+', '_', t)

    slug = slugify(name)
    existing = EntityType.query.filter_by(org_id=current_user.org_id, slug=slug).first()
    if existing:
        # reuse and link if not already linked
        et = existing
    else:
        et = EntityType(
            org_id=current_user.org_id,
            created_by=current_user.id,
            name=name,
            slug=slug,
            description=request.form.get('description', ''),
            icon=request.form.get('icon', '📋'),
            is_active=True,
        )
        db.session.add(et)
        db.session.flush()

    if not AppEntityType.query.filter_by(
        application_id=app_record.id, entity_type_id=et.id
    ).first():
        db.session.add(AppEntityType(application_id=app_record.id, entity_type_id=et.id))

    db.session.commit()
    flash(f'Data type "{name}" created and linked to {app_record.name}.', 'success')
    return redirect(url_for('entities.builder', entity_id=et.id, app_id=app_id))


@applications_bp.route('/<int:app_id>/entity/<int:et_id>/save-fields', methods=['POST'])
@login_required
@require_role('admin')
def save_entity_fields(app_id, et_id):
    import json, re
    app_record = Application.query.filter_by(id=app_id, org_id=current_user.org_id).first_or_404()
    et = EntityType.query.filter_by(id=et_id, org_id=current_user.org_id).first_or_404()

    fields_json = request.form.get('fields_data', '[]')
    try:
        fields_data = json.loads(fields_json)
    except Exception:
        flash('Invalid field data.', 'error')
        return redirect(url_for('applications.builder', app_id=app_id, panel=f'et_{et_id}'))

    def slugify(text):
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        return re.sub(r'[\s_-]+', '_', text)

    kept_ids = set()
    for idx, fd in enumerate(fields_data):
        field_id = fd.get('id')
        if field_id:
            field = EntityField.query.get(int(field_id))
            if field and field.entity_type_id == et.id:
                kept_ids.add(field.id)
        else:
            fname = slugify(fd.get('label', f'field_{idx}'))
            base = fname
            c = 1
            while EntityField.query.filter_by(entity_type_id=et.id, name=fname).first():
                fname = f'{base}_{c}'; c += 1
            field = EntityField(entity_type_id=et.id, created_by=current_user.id, name=fname)
            db.session.add(field)
            db.session.flush()
            kept_ids.add(field.id)

        field.label = fd.get('label', field.name)
        field.field_type = fd.get('field_type', 'text')
        field.is_required = fd.get('is_required', False)
        field.is_unique = fd.get('is_unique', False)
        field.display_in_list = fd.get('display_in_list', False)
        field.order = idx
        field.set_options_list(fd.get('options', []))
        lid = fd.get('lookup_entity_type_id')
        field.lookup_entity_type_id = int(lid) if lid else None
        field.lookup_source = fd.get('lookup_source') or 'entity'
        field.default_value = fd.get('default_value') or None
        field.display_condition = fd.get('display_condition') or None
        field.calculated_formula = fd.get('calculated_formula') or None

    for f in EntityField.query.filter(
        EntityField.entity_type_id == et.id,
        EntityField.id.notin_(kept_ids)
    ).all():
        db.session.delete(f)

    db.session.commit()
    flash(f'Fields saved for "{et.name}".', 'success')
    return redirect(url_for('applications.builder', app_id=app_id, panel=f'et_{et_id}'))


@applications_bp.route('/<int:app_id>/add-form', methods=['POST'])
@login_required
@require_role('admin')
def add_form(app_id):
    from app.models.application import AppForm
    app_record = Application.query.filter_by(id=app_id, org_id=current_user.org_id).first_or_404()
    name = request.form.get('name', '').strip()
    entity_type_id = request.form.get('entity_type_id', type=int)
    if not name or not entity_type_id:
        flash('Form name and data type are required.', 'error')
        return redirect(url_for('applications.builder', app_id=app_id))
    form = Form(
        org_id=current_user.org_id,
        created_by=current_user.id,
        name=name,
        entity_type_id=entity_type_id,
        is_active=True,
    )
    db.session.add(form)
    db.session.flush()
    if not AppForm.query.filter_by(application_id=app_record.id, form_id=form.id).first():
        db.session.add(AppForm(application_id=app_record.id, form_id=form.id))
    db.session.commit()
    flash(f'Form "{name}" created.', 'success')
    return redirect(url_for('applications.builder', app_id=app_id, panel=f'form_{form.id}'))


@applications_bp.route('/<int:app_id>/entity/<int:et_id>/settings', methods=['POST'])
@login_required
@require_role('admin')
def save_entity_settings(app_id, et_id):
    et = EntityType.query.filter_by(id=et_id, org_id=current_user.org_id).first_or_404()
    et.name = request.form.get('name', et.name).strip() or et.name
    et.icon = request.form.get('icon', et.icon or '').strip() or et.icon
    et.description = request.form.get('description', '').strip() or None
    et.form_mode = request.form.get('form_mode', 'create')
    db.session.commit()
    flash('Form settings saved.', 'success')
    return redirect(url_for('applications.builder', app_id=app_id, panel=f'et_{et_id}'))


@applications_bp.route('/<int:app_id>/remove-entity/<int:et_id>', methods=['POST'])
@login_required
@require_role('admin')
def remove_entity(app_id, et_id):
    link = AppEntityType.query.filter_by(
        application_id=app_id, entity_type_id=et_id
    ).first_or_404()
    db.session.delete(link)
    db.session.commit()
    flash('Data type removed from app.', 'success')
    return redirect(url_for('applications.builder', app_id=app_id))


@applications_bp.route('/<int:app_id>/delete', methods=['POST'])
@login_required
@require_role('admin')
def delete_app(app_id):
    app_record = Application.query.filter_by(
        id=app_id, org_id=current_user.org_id
    ).first_or_404()
    app_record.is_active = False
    db.session.commit()
    flash(f'"{app_record.name}" removed.', 'success')
    return redirect(url_for('applications.manage'))


@applications_bp.route('/templates')
@login_required
@require_role('admin')
def templates_catalogue():
    from app.app_registry import all_templates
    templates = all_templates()
    installed_keys = {
        a.template_key
        for a in Application.query.filter_by(
            org_id=current_user.org_id, is_active=True
        ).all()
        if a.template_key
    }
    return render_template('applications/templates.html',
                           templates=templates,
                           installed_keys=installed_keys)


@applications_bp.route('/templates/<key>/install', methods=['POST'])
@login_required
@require_role('admin')
def install_template(key):
    app_record, error = install_from_template(key, current_user.org_id, current_user.id)
    if error and error != 'Already installed.':
        flash(error, 'error')
        return redirect(url_for('applications.templates_catalogue'))
    if error == 'Already installed.':
        flash('This template is already installed.', 'error')
        return redirect(url_for('applications.templates_catalogue'))
    flash(f'"{app_record.name}" installed successfully. Configure it below.', 'success')
    return redirect(url_for('applications.builder', app_id=app_record.id))
