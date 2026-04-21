import json
from flask import Blueprint, jsonify, request, g
from app.extensions import db
from app.models.form import Form, FormSubmission
from app.models.record import Record, RecordValue, RecordLink
from app.utils.decorators import api_auth
from app.utils.visibility import visible_unit_ids
from app.utils.serialisers import form_to_dict, record_to_dict

api_forms_bp = Blueprint('api_forms', __name__, url_prefix='/api/v1/forms')


@api_forms_bp.route('/')
@api_auth
def list_forms():
    user = g.current_api_user
    forms = Form.query.filter_by(org_id=user.org_id, is_active=True).all()
    return jsonify({
        'status': 'ok',
        'data': [form_to_dict(f) for f in forms],
        'meta': {'total': len(forms)}
    })


@api_forms_bp.route('/<int:form_id>')
@api_auth
def get_form(form_id):
    user = g.current_api_user
    form = Form.query.filter_by(id=form_id, org_id=user.org_id, is_active=True).first()
    if not form:
        return jsonify({'status': 'error', 'code': 'NOT_FOUND', 'message': 'Form not found'}), 404
    return jsonify({'status': 'ok', 'data': form_to_dict(form)})


@api_forms_bp.route('/<int:form_id>/submit', methods=['POST'])
@api_auth
def submit_form(form_id):
    user = g.current_api_user
    form = Form.query.filter_by(id=form_id, org_id=user.org_id, is_active=True).first()
    if not form:
        return jsonify({'status': 'error', 'code': 'NOT_FOUND', 'message': 'Form not found'}), 404

    data = request.get_json() or {}
    org_unit_id = data.get('org_unit_id')
    if not org_unit_id:
        return jsonify({'status': 'error', 'code': 'BAD_REQUEST', 'message': 'org_unit_id required'}), 400

    unit_ids = visible_unit_ids(user.id)
    if org_unit_id not in unit_ids:
        return jsonify({'status': 'error', 'code': 'FORBIDDEN', 'message': 'Org unit not in scope'}), 403

    et = form.entity_type
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
    raw_data = {}
    for ff in form.form_fields.filter_by(is_visible=True).all():
        field = ff.entity_field
        if not field:
            continue
        if field.name in values:
            raw_val = values[field.name]
            raw_data[field.name] = raw_val
            rv = RecordValue(record_id=record.id, entity_field_id=field.id,
                             value_text=str(raw_val))
            if field.field_type == 'number':
                try:
                    rv.value_number = float(raw_val)
                except (ValueError, TypeError):
                    pass
            db.session.add(rv)

            if field.field_type == 'lookup' and raw_val:
                try:
                    db.session.add(RecordLink(
                        source_record_id=record.id,
                        target_record_id=int(raw_val),
                        entity_field_id=field.id
                    ))
                except (ValueError, TypeError):
                    pass

    db.session.flush()
    record.compute_display_label()

    db.session.add(FormSubmission(
        form_id=form.id,
        record_id=record.id,
        submitted_by=user.id,
        org_unit_id=org_unit_id,
        raw_data=json.dumps(raw_data),
    ))
    db.session.commit()

    return jsonify({'status': 'ok', 'data': record_to_dict(record)}), 201
