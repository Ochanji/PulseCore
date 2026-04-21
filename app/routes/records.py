from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.entity import EntityType, EntityField
from app.models.record import Record, RecordValue, RecordLink
from app.models.org_unit import OrgUnit
from app.models.application import AppEntityType
from app.utils.visibility import visible_unit_ids

records_bp = Blueprint('records', __name__, url_prefix='/records')


def save_record_values(record, entity_type, form_data):
    fields = entity_type.fields.all()
    for field in fields:
        raw_value = form_data.get(f'field_{field.id}')
        if raw_value is None:
            continue

        if field.field_type == 'boolean':
            raw_value = 'true' if raw_value in ('on', 'true', '1') else 'false'

        rv = RecordValue.query.filter_by(record_id=record.id, entity_field_id=field.id).first()
        if not rv:
            rv = RecordValue(record_id=record.id, entity_field_id=field.id)
            db.session.add(rv)

        rv.value_text = raw_value
        if field.field_type in ('number',):
            try:
                rv.value_number = float(raw_value)
            except (ValueError, TypeError):
                rv.value_number = None

        if field.field_type == 'lookup' and raw_value:
            try:
                target_id = int(raw_value)
                existing = RecordLink.query.filter_by(
                    source_record_id=record.id, entity_field_id=field.id
                ).first()
                if existing:
                    existing.target_record_id = target_id
                else:
                    link = RecordLink(
                        source_record_id=record.id,
                        target_record_id=target_id,
                        entity_field_id=field.id
                    )
                    db.session.add(link)
            except (ValueError, TypeError):
                pass

    db.session.flush()
    record.compute_display_label()


@records_bp.route('/<int:entity_type_id>/')
@login_required
def list_records(entity_type_id):
    et = EntityType.query.filter_by(id=entity_type_id, org_id=current_user.org_id).first_or_404()
    unit_ids = visible_unit_ids(current_user.id)

    q = Record.query.filter(
        Record.entity_type_id == et.id,
        Record.org_unit_id.in_(unit_ids),
        Record.is_active == True
    )

    search = request.args.get('q', '').strip()
    if search:
        q = q.filter(Record.display_label.like(f'%{search}%'))

    filter_unit = request.args.get('org_unit_id')
    if filter_unit:
        q = q.filter(Record.org_unit_id == int(filter_unit))

    records = q.order_by(Record.updated_at.desc()).all()
    list_fields = EntityField.query.filter_by(
        entity_type_id=et.id, display_in_list=True
    ).order_by(EntityField.order).all()

    visible_units = OrgUnit.query.filter(OrgUnit.id.in_(unit_ids)).order_by(OrgUnit.name).all()

    app_link = AppEntityType.query.filter_by(entity_type_id=et.id).first()
    parent_app = app_link.application if app_link else None

    return render_template('records/list.html',
                           entity_type=et,
                           records=records,
                           list_fields=list_fields,
                           visible_units=visible_units,
                           search=search,
                           parent_app=parent_app)


@records_bp.route('/<int:entity_type_id>/new', methods=['GET', 'POST'])
@login_required
def create_record(entity_type_id):
    et = EntityType.query.filter_by(id=entity_type_id, org_id=current_user.org_id).first_or_404()
    unit_ids = visible_unit_ids(current_user.id)
    visible_units = OrgUnit.query.filter(OrgUnit.id.in_(unit_ids)).order_by(OrgUnit.name).all()

    parent_record = None
    parent_id = request.args.get('parent_id') or request.form.get('parent_record_id')
    if parent_id:
        parent_record = Record.query.get(int(parent_id))

    all_entity_types = EntityType.query.filter_by(org_id=current_user.org_id, is_active=True).all()

    if request.method == 'POST':
        org_unit_id = request.form.get('org_unit_id')
        if not org_unit_id or int(org_unit_id) not in unit_ids:
            flash('Select a valid org unit.', 'error')
            return render_template('records/create.html', entity_type=et,
                                   visible_units=visible_units, parent_record=parent_record,
                                   all_entity_types=all_entity_types)

        record = Record(
            org_id=current_user.org_id,
            entity_type_id=et.id,
            org_unit_id=int(org_unit_id),
            parent_record_id=int(parent_id) if parent_id else None,
            created_by=current_user.id,
            display_label=f'New {et.name}',
        )
        db.session.add(record)
        db.session.flush()

        save_record_values(record, et, request.form)
        db.session.commit()
        flash(f'{et.name} record created.', 'success')
        return redirect(url_for('records.detail', entity_type_id=et.id, record_id=record.id))

    return render_template('records/create.html',
                           entity_type=et,
                           visible_units=visible_units,
                           parent_record=parent_record,
                           all_entity_types=all_entity_types)


@records_bp.route('/<int:entity_type_id>/<int:record_id>')
@login_required
def detail(entity_type_id, record_id):
    et = EntityType.query.filter_by(id=entity_type_id, org_id=current_user.org_id).first_or_404()
    unit_ids = visible_unit_ids(current_user.id)
    record = Record.query.filter(
        Record.id == record_id,
        Record.entity_type_id == et.id,
        Record.org_unit_id.in_(unit_ids),
        Record.is_active == True
    ).first_or_404()

    fields = et.fields.order_by(EntityField.order).all()

    child_entity_types = EntityType.query.filter_by(
        parent_entity_type_id=et.id, org_id=current_user.org_id, is_active=True
    ).all()
    children_by_type = {}
    for cet in child_entity_types:
        children_by_type[cet] = Record.query.filter_by(
            parent_record_id=record.id, entity_type_id=cet.id, is_active=True
        ).all()

    outgoing_links = record.outgoing_links.all()
    incoming_links = record.incoming_links.all()

    return render_template('records/detail.html',
                           entity_type=et,
                           record=record,
                           fields=fields,
                           children_by_type=children_by_type,
                           outgoing_links=outgoing_links,
                           incoming_links=incoming_links)


@records_bp.route('/<int:entity_type_id>/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_record(entity_type_id, record_id):
    et = EntityType.query.filter_by(id=entity_type_id, org_id=current_user.org_id).first_or_404()
    unit_ids = visible_unit_ids(current_user.id)
    record = Record.query.filter(
        Record.id == record_id,
        Record.entity_type_id == et.id,
        Record.org_unit_id.in_(unit_ids)
    ).first_or_404()

    if request.method == 'POST':
        new_unit = request.form.get('org_unit_id')
        if new_unit and int(new_unit) in unit_ids:
            record.org_unit_id = int(new_unit)
        save_record_values(record, et, request.form)
        db.session.commit()
        flash('Record updated.', 'success')
        return redirect(url_for('records.list_records', entity_type_id=et.id))

    visible_units = OrgUnit.query.filter(OrgUnit.id.in_(unit_ids)).order_by(OrgUnit.name).all()
    fields = et.fields.order_by(EntityField.order).all()
    return render_template('records/edit.html',
                           entity_type=et,
                           record=record,
                           fields=fields,
                           visible_units=visible_units)


@records_bp.route('/<int:entity_type_id>/<int:record_id>/link', methods=['POST'])
@login_required
def add_link(entity_type_id, record_id):
    unit_ids = visible_unit_ids(current_user.id)
    record = Record.query.filter(
        Record.id == record_id,
        Record.org_unit_id.in_(unit_ids)
    ).first_or_404()

    target_id = request.form.get('target_record_id')
    if target_id:
        link = RecordLink(
            source_record_id=record.id,
            target_record_id=int(target_id),
            entity_field_id=None
        )
        db.session.add(link)
        db.session.commit()
        flash('Record linked.', 'success')

    return redirect(url_for('records.detail', entity_type_id=entity_type_id, record_id=record_id))
