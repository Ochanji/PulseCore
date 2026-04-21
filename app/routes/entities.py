import json
import re
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.entity import EntityType, EntityField
from app.utils.decorators import require_role

entities_bp = Blueprint('entities', __name__, url_prefix='/entities')


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    return text


@entities_bp.route('/')
@login_required
def list_entities():
    entity_types = EntityType.query.filter_by(
        org_id=current_user.org_id, is_active=True
    ).order_by(EntityType.name).all()
    return render_template('entities/list.html', entity_types=entity_types)


@entities_bp.route('/new', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def new_entity():
    entity_types = EntityType.query.filter_by(org_id=current_user.org_id, is_active=True).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Name is required.', 'error')
            return render_template('entities/list.html', entity_types=entity_types, show_modal=True)

        slug = slugify(name)
        existing = EntityType.query.filter_by(org_id=current_user.org_id, slug=slug).first()
        if existing:
            flash('An entity type with this name already exists.', 'error')
            return render_template('entities/list.html', entity_types=entity_types, show_modal=True)

        parent_id = request.form.get('parent_entity_type_id') or None
        if parent_id:
            parent_id = int(parent_id)

        et = EntityType(
            org_id=current_user.org_id,
            created_by=current_user.id,
            name=name,
            slug=slug,
            description=request.form.get('description', ''),
            icon=request.form.get('icon', ''),
            is_lookup=request.form.get('is_lookup') == 'on',
            parent_entity_type_id=parent_id,
        )
        db.session.add(et)
        db.session.commit()
        flash(f'Entity type "{name}" created.', 'success')
        return redirect(url_for('entities.builder', entity_id=et.id))

    return render_template('entities/list.html', entity_types=entity_types, show_modal=True)


@entities_bp.route('/<int:entity_id>')
@login_required
def detail(entity_id):
    et = EntityType.query.filter_by(id=entity_id, org_id=current_user.org_id).first_or_404()
    from app.models.record import Record
    record_count = Record.query.filter_by(entity_type_id=et.id, is_active=True).count()
    return render_template('entities/detail.html', entity_type=et, record_count=record_count)


@entities_bp.route('/<int:entity_id>/fields', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def builder(entity_id):
    et = EntityType.query.filter_by(id=entity_id, org_id=current_user.org_id).first_or_404()
    all_entity_types = EntityType.query.filter_by(org_id=current_user.org_id, is_active=True).all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_entity':
            name = request.form.get('name', '').strip()
            if name:
                et.name = name
                et.slug = slugify(name)
            et.description = request.form.get('description', '')
            et.icon = request.form.get('icon', '')
            et.is_lookup = request.form.get('is_lookup') == 'on'
            parent_id = request.form.get('parent_entity_type_id') or None
            et.parent_entity_type_id = int(parent_id) if parent_id else None
            db.session.commit()
            flash('Entity type updated.', 'success')
            return redirect(url_for('entities.builder', entity_id=entity_id))

        if action == 'save_fields':
            fields_json = request.form.get('fields_data', '[]')
            try:
                fields_data = json.loads(fields_json)
            except Exception:
                flash('Invalid field data.', 'error')
                return redirect(url_for('entities.builder', entity_id=entity_id))

            existing_field_ids = set()
            for idx, fd in enumerate(fields_data):
                field_id = fd.get('id')
                if field_id:
                    field = EntityField.query.get(int(field_id))
                    if field and field.entity_type_id == et.id:
                        existing_field_ids.add(field.id)
                else:
                    field_name = slugify(fd.get('label', f'field_{idx}'))
                    base_name = field_name
                    counter = 1
                    while EntityField.query.filter_by(entity_type_id=et.id, name=field_name).first():
                        field_name = f'{base_name}_{counter}'
                        counter += 1
                    field = EntityField(
                        entity_type_id=et.id,
                        created_by=current_user.id,
                        name=field_name,
                    )
                    db.session.add(field)
                    db.session.flush()
                    existing_field_ids.add(field.id)

                field.label = fd.get('label', field.name)
                field.field_type = fd.get('field_type', 'text')
                field.is_required = fd.get('is_required', False)
                field.is_unique = fd.get('is_unique', False)
                field.display_in_list = fd.get('display_in_list', False)
                field.order = idx
                options = fd.get('options', [])
                field.set_options_list(options)
                lookup_id = fd.get('lookup_entity_type_id')
                field.lookup_entity_type_id = int(lookup_id) if lookup_id else None

            to_delete = EntityField.query.filter(
                EntityField.entity_type_id == et.id,
                EntityField.id.notin_(existing_field_ids)
            ).all()
            for f in to_delete:
                db.session.delete(f)

            db.session.commit()
            flash('Fields saved.', 'success')
            return redirect(url_for('entities.builder', entity_id=entity_id))

    fields = et.fields.order_by(EntityField.order).all()
    app_id = request.args.get('app_id', type=int)
    return render_template('entities/builder.html',
                           entity_type=et,
                           fields=fields,
                           all_entity_types=all_entity_types,
                           field_types=EntityField.FIELD_TYPES,
                           app_id=app_id)


@entities_bp.route('/<int:entity_id>/delete', methods=['POST'])
@login_required
@require_role('admin')
def delete_entity(entity_id):
    et = EntityType.query.filter_by(id=entity_id, org_id=current_user.org_id).first_or_404()
    et.is_active = False
    db.session.commit()
    flash(f'Entity type "{et.name}" deactivated.', 'success')
    return redirect(url_for('entities.list_entities'))
