import json
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.entity import EntityType, EntityField
from app.models.form import Form, FormField, FormSubmission
from app.models.record import Record, RecordValue, RecordLink
from app.models.org_unit import OrgUnit
from app.utils.decorators import require_role
from app.utils.visibility import visible_unit_ids

forms_bp = Blueprint('forms', __name__, url_prefix='/forms')


@forms_bp.route('/')
@login_required
def list_forms():
    forms = Form.query.filter_by(org_id=current_user.org_id).order_by(Form.name).all()
    return render_template('forms/list.html', forms=forms)


@forms_bp.route('/new', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def new_form():
    entity_types = EntityType.query.filter_by(org_id=current_user.org_id, is_active=True).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        entity_type_id = request.form.get('entity_type_id')
        if not name or not entity_type_id:
            flash('Name and entity type are required.', 'error')
            return render_template('forms/list.html', forms=[], entity_types=entity_types, show_modal=True)

        form = Form(
            org_id=current_user.org_id,
            created_by=current_user.id,
            name=name,
            description=request.form.get('description', ''),
            entity_type_id=int(entity_type_id),
        )
        db.session.add(form)
        db.session.commit()
        flash(f'Form "{name}" created.', 'success')
        return redirect(url_for('forms.builder', form_id=form.id))

    forms = Form.query.filter_by(org_id=current_user.org_id).all()
    return render_template('forms/list.html', forms=forms, entity_types=entity_types, show_modal=True)


@forms_bp.route('/<int:form_id>/builder', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def builder(form_id):
    form = Form.query.filter_by(id=form_id, org_id=current_user.org_id).first_or_404()
    et = form.entity_type
    all_fields = et.fields.order_by(EntityField.order).all()

    if request.method == 'POST':
        selected_field_ids = request.form.getlist('field_ids')
        FormField.query.filter_by(form_id=form.id).delete()

        for idx, fid in enumerate(selected_field_ids):
            ff = FormField(
                form_id=form.id,
                entity_field_id=int(fid),
                order=idx,
                is_visible=True,
                help_text=request.form.get(f'help_{fid}', ''),
            )
            db.session.add(ff)

        form.version += 1
        db.session.commit()
        flash('Form fields saved.', 'success')
        return redirect(url_for('forms.builder', form_id=form.id))

    included_ids = {ff.entity_field_id for ff in form.form_fields}
    return render_template('forms/builder.html',
                           form=form,
                           entity_type=et,
                           all_fields=all_fields,
                           included_ids=included_ids)


@forms_bp.route('/<int:form_id>/preview')
@login_required
def preview(form_id):
    form = Form.query.filter_by(id=form_id, org_id=current_user.org_id).first_or_404()
    form_fields = form.form_fields.filter_by(is_visible=True).order_by(FormField.order).all()
    return render_template('forms/submit.html', form=form, form_fields=form_fields,
                           is_preview=True, record=None)


@forms_bp.route('/<int:form_id>/submit', methods=['GET', 'POST'])
@login_required
def submit(form_id):
    form_obj = Form.query.filter_by(id=form_id, org_id=current_user.org_id, is_active=True).first_or_404()
    unit_ids = visible_unit_ids(current_user.id)
    visible_units = OrgUnit.query.filter(OrgUnit.id.in_(unit_ids)).order_by(OrgUnit.name).all()
    form_fields = form_obj.form_fields.filter_by(is_visible=True).order_by(FormField.order).all()
    et = form_obj.entity_type

    parent_record = None
    parent_id = request.args.get('parent_id') or request.form.get('parent_record_id')
    if parent_id:
        parent_record = Record.query.get(int(parent_id))

    if request.method == 'POST':
        org_unit_id = request.form.get('org_unit_id')
        if not org_unit_id or int(org_unit_id) not in unit_ids:
            flash('Select a valid org unit.', 'error')
            return render_template('forms/submit.html', form=form_obj, form_fields=form_fields,
                                   visible_units=visible_units, is_preview=False, record=None,
                                   parent_record=parent_record)

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

        raw_data = {}
        for ff in form_fields:
            field = ff.entity_field
            raw_value = request.form.get(f'field_{field.id}')
            if raw_value is None:
                continue

            raw_data[field.name] = raw_value

            if field.field_type == 'boolean':
                raw_value = 'true' if raw_value in ('on', 'true', '1') else 'false'

            rv = RecordValue(record_id=record.id, entity_field_id=field.id, value_text=raw_value)
            if field.field_type == 'number':
                try:
                    rv.value_number = float(raw_value)
                except (ValueError, TypeError):
                    pass
            db.session.add(rv)

            if field.field_type == 'lookup' and raw_value:
                try:
                    link = RecordLink(
                        source_record_id=record.id,
                        target_record_id=int(raw_value),
                        entity_field_id=field.id
                    )
                    db.session.add(link)
                except (ValueError, TypeError):
                    pass

        db.session.flush()
        record.compute_display_label()

        submission = FormSubmission(
            form_id=form_obj.id,
            record_id=record.id,
            submitted_by=current_user.id,
            org_unit_id=int(org_unit_id),
            raw_data=json.dumps(raw_data),
        )
        db.session.add(submission)
        db.session.commit()

        flash(f'{et.name} record submitted successfully.', 'success')
        return redirect(url_for('records.detail', entity_type_id=et.id, record_id=record.id))

    return render_template('forms/submit.html',
                           form=form_obj,
                           form_fields=form_fields,
                           visible_units=visible_units,
                           is_preview=False,
                           record=None,
                           parent_record=parent_record)


@forms_bp.route('/<int:form_id>/submissions')
@login_required
def submissions(form_id):
    form = Form.query.filter_by(id=form_id, org_id=current_user.org_id).first_or_404()
    subs = form.submissions.order_by(FormSubmission.submitted_at.desc()).all()
    return render_template('forms/submissions.html', form=form, submissions=subs)
