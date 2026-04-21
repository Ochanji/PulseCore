from datetime import datetime
from flask import Blueprint, jsonify, request, g
from app.extensions import db
from app.models.entity import EntityType, EntityField
from app.models.record import Record, RecordValue, RecordLink
from app.utils.decorators import api_auth
from app.utils.visibility import visible_unit_ids
from app.utils.serialisers import record_to_dict

api_records_bp = Blueprint('api_records', __name__, url_prefix='/api/v1/records')


@api_records_bp.route('/<int:entity_type_id>/')
@api_auth
def list_records(entity_type_id):
    user = g.current_api_user
    et = EntityType.query.filter_by(id=entity_type_id, org_id=user.org_id, is_active=True).first()
    if not et:
        return jsonify({'status': 'error', 'code': 'NOT_FOUND', 'message': 'Entity type not found'}), 404

    unit_ids = visible_unit_ids(user.id)
    q = Record.query.filter(
        Record.entity_type_id == et.id,
        Record.org_unit_id.in_(unit_ids),
        Record.is_active == True
    )

    parent_id = request.args.get('parent_id')
    if parent_id:
        q = q.filter(Record.parent_record_id == int(parent_id))

    org_unit_id = request.args.get('org_unit_id')
    if org_unit_id:
        q = q.filter(Record.org_unit_id == int(org_unit_id))

    since = request.args.get('since')
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            q = q.filter(Record.updated_at >= since_dt)
        except ValueError:
            pass

    search = request.args.get('q', '').strip()
    if search:
        q = q.filter(Record.display_label.like(f'%{search}%'))

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    total = q.count()
    records = q.order_by(Record.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'status': 'ok',
        'data': [record_to_dict(r) for r in records],
        'meta': {'page': page, 'per_page': per_page, 'total': total}
    })


@api_records_bp.route('/<int:entity_type_id>/', methods=['POST'])
@api_auth
def create_record(entity_type_id):
    user = g.current_api_user
    et = EntityType.query.filter_by(id=entity_type_id, org_id=user.org_id, is_active=True).first()
    if not et:
        return jsonify({'status': 'error', 'code': 'NOT_FOUND', 'message': 'Entity type not found'}), 404

    data = request.get_json() or {}
    org_unit_id = data.get('org_unit_id')
    if not org_unit_id:
        return jsonify({'status': 'error', 'code': 'BAD_REQUEST', 'message': 'org_unit_id required'}), 400

    unit_ids = visible_unit_ids(user.id)
    if org_unit_id not in unit_ids:
        return jsonify({'status': 'error', 'code': 'FORBIDDEN', 'message': 'Org unit not in scope'}), 403

    record = Record(
        org_id=user.org_id,
        entity_type_id=et.id,
        org_unit_id=org_unit_id,
        parent_record_id=data.get('parent_record_id'),
        created_by=user.id,
        display_label=f'New {et.name}',
    )
    db.session.add(record)
    db.session.flush()

    values = data.get('values', {})
    for field in et.fields.all():
        if field.name in values:
            rv = RecordValue(record_id=record.id, entity_field_id=field.id,
                             value_text=str(values[field.name]))
            if field.field_type == 'number':
                try:
                    rv.value_number = float(values[field.name])
                except (ValueError, TypeError):
                    pass
            db.session.add(rv)

    db.session.flush()
    record.compute_display_label()
    db.session.commit()

    return jsonify({'status': 'ok', 'data': record_to_dict(record)}), 201


@api_records_bp.route('/<int:entity_type_id>/<int:record_id>')
@api_auth
def get_record(entity_type_id, record_id):
    user = g.current_api_user
    unit_ids = visible_unit_ids(user.id)
    record = Record.query.filter(
        Record.id == record_id,
        Record.entity_type_id == entity_type_id,
        Record.org_unit_id.in_(unit_ids),
        Record.is_active == True
    ).first()
    if not record:
        return jsonify({'status': 'error', 'code': 'NOT_FOUND', 'message': 'Record not found'}), 404

    d = record_to_dict(record)
    d['children'] = [record_to_dict(c) for c in record.children.filter_by(is_active=True).all()]
    d['links'] = [{'target_id': lnk.target_record_id,
                   'field': lnk.entity_field.name if lnk.entity_field else None}
                  for lnk in record.outgoing_links.all()]
    return jsonify({'status': 'ok', 'data': d})


@api_records_bp.route('/<int:entity_type_id>/<int:record_id>', methods=['PUT'])
@api_auth
def update_record(entity_type_id, record_id):
    user = g.current_api_user
    unit_ids = visible_unit_ids(user.id)
    record = Record.query.filter(
        Record.id == record_id,
        Record.entity_type_id == entity_type_id,
        Record.org_unit_id.in_(unit_ids),
        Record.is_active == True
    ).first()
    if not record:
        return jsonify({'status': 'error', 'code': 'NOT_FOUND', 'message': 'Record not found'}), 404

    data = request.get_json() or {}
    values = data.get('values', {})
    et = record.entity_type

    for field in et.fields.all():
        if field.name in values:
            rv = RecordValue.query.filter_by(record_id=record.id, entity_field_id=field.id).first()
            if not rv:
                rv = RecordValue(record_id=record.id, entity_field_id=field.id)
                db.session.add(rv)
            rv.value_text = str(values[field.name])
            if field.field_type == 'number':
                try:
                    rv.value_number = float(values[field.name])
                except (ValueError, TypeError):
                    pass

    db.session.flush()
    record.compute_display_label()
    db.session.commit()

    return jsonify({'status': 'ok', 'data': record_to_dict(record)})
