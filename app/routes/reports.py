import io
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.entity import EntityType, EntityField
from app.models.record import Record
from app.models.org_unit import OrgUnit
from app.utils.visibility import visible_unit_ids
from app.utils.decorators import require_role

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

ALLOWED_ROLES = ['admin', 'supervisor', 'district_manager', 'report_viewer']


def _require_report_access():
    if not current_user.is_superadmin:
        user_roles = [a.role for a in current_user.unit_assignments]
        if not any(r in ALLOWED_ROLES for r in user_roles):
            return False
    return True


def _build_query(entity_type_id, org_unit_id, date_from, date_to):
    from app.utils.visibility import visible_program_ids
    unit_ids = visible_unit_ids(current_user.id)
    prog_ids = visible_program_ids(current_user)

    q = Record.query.filter(
        Record.entity_type_id == entity_type_id,
        Record.org_unit_id.in_(unit_ids),
        Record.is_active == True,
        # scope to user's program spaces (NULL program_id = legacy/unassigned, always visible)
        db.or_(
            Record.program_id.in_(prog_ids),
            Record.program_id.is_(None),
        ),
    )

    if org_unit_id:
        # include the selected unit and all its descendants
        selected = OrgUnit.query.get(int(org_unit_id))
        if selected:
            sub_ids = [
                u.id for u in OrgUnit.query.filter(
                    OrgUnit.path.like(selected.path + '%'),
                    OrgUnit.is_active == True,
                ).all()
                if u.id in unit_ids
            ]
            q = q.filter(Record.org_unit_id.in_(sub_ids))

    if date_from:
        try:
            q = q.filter(Record.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(Record.created_at <= datetime.strptime(date_to, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59))
        except ValueError:
            pass

    return q


@reports_bp.route('/')
@login_required
def index():
    if not _require_report_access():
        flash('You do not have permission to access reports.', 'error')
        return redirect(url_for('dashboard.index'))

    entity_types = EntityType.query.filter_by(
        org_id=current_user.org_id, is_active=True
    ).order_by(EntityType.name).all()

    unit_ids = visible_unit_ids(current_user.id)
    visible_units = OrgUnit.query.filter(
        OrgUnit.id.in_(unit_ids)
    ).order_by(OrgUnit.level, OrgUnit.name).all()

    # Build preview if filters submitted
    preview_records = []
    preview_fields = []
    total_count = 0
    selected_et = None

    entity_type_id = request.args.get('entity_type_id', type=int)
    org_unit_id = request.args.get('org_unit_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    fmt = request.args.get('format', 'csv')
    aggregate = request.args.get('aggregate', '0')

    if entity_type_id:
        selected_et = EntityType.query.filter_by(
            id=entity_type_id, org_id=current_user.org_id
        ).first()
        if selected_et:
            q = _build_query(entity_type_id, org_unit_id or None,
                             date_from or None, date_to or None)
            total_count = q.count()
            preview_records = q.order_by(Record.created_at.desc()).limit(10).all()
            preview_fields = EntityField.query.filter_by(
                entity_type_id=entity_type_id
            ).order_by(EntityField.order).all()

    return render_template(
        'reports/index.html',
        entity_types=entity_types,
        visible_units=visible_units,
        selected_et=selected_et,
        preview_records=preview_records,
        preview_fields=preview_fields,
        total_count=total_count,
        # preserve filter state
        sel_entity_type_id=entity_type_id,
        sel_org_unit_id=org_unit_id,
        sel_date_from=date_from,
        sel_date_to=date_to,
        sel_format=fmt,
        sel_aggregate=aggregate,
    )


@reports_bp.route('/export')
@login_required
def export():
    if not _require_report_access():
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.index'))

    entity_type_id = request.args.get('entity_type_id', type=int)
    org_unit_id = request.args.get('org_unit_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    fmt = request.args.get('format', 'csv')
    aggregate = request.args.get('aggregate', '0') == '1'

    if not entity_type_id:
        flash('Select an entity type to export.', 'error')
        return redirect(url_for('reports.index'))

    et = EntityType.query.filter_by(
        id=entity_type_id, org_id=current_user.org_id
    ).first_or_404()

    q = _build_query(entity_type_id, org_unit_id or None,
                     date_from or None, date_to or None)
    records = q.order_by(Record.created_at.asc()).all()

    fields = EntityField.query.filter_by(
        entity_type_id=entity_type_id
    ).order_by(EntityField.order).all()

    date_str = datetime.utcnow().strftime('%Y%m%d')
    slug = et.slug

    from app.utils import export as exp

    if fmt == 'excel':
        if aggregate:
            buf = exp.export_aggregate_excel(records, et)
            filename = f'{slug}_aggregate_{date_str}.xlsx'
        else:
            buf = exp.export_records_excel(records, et, fields)
            filename = f'{slug}_records_{date_str}.xlsx'
        return send_file(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )

    elif fmt == 'dhis2':
        json_str = exp.export_dhis2_json(records, et)
        buf = io.BytesIO(json_str.encode('utf-8'))
        filename = f'{slug}_dhis2_{date_str}.json'
        return send_file(
            buf,
            mimetype='application/json',
            as_attachment=True,
            download_name=filename,
        )

    else:  # csv default
        if aggregate:
            buf = exp.export_aggregate_csv(records, et)
            filename = f'{slug}_aggregate_{date_str}.csv'
        else:
            buf = exp.export_records_csv(records, et, fields)
            filename = f'{slug}_records_{date_str}.csv'

        buf_bytes = io.BytesIO(buf.getvalue().encode('utf-8'))
        return send_file(
            buf_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename,
        )
