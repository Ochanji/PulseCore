from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.indicator import Indicator, IndicatorTarget, IndicatorValue, AGGREGATION_TYPES, TARGET_TYPES
from app.models.program import Program, SECTORS
from app.models.entity import EntityType, EntityField
from app.models.org_unit import OrgUnit
from app.models.record import Record, RecordValue
from app.utils.visibility import visible_unit_ids
from datetime import datetime

indicators_bp = Blueprint('indicators', __name__, url_prefix='/indicators')


def _require_access():
    from app.utils.role_access import can_access
    if not current_user.is_superadmin and not can_access('indicators'):
        flash('Access denied.', 'error')
        return False
    return True


def _compute_indicator_value(indicator, org_unit_id, year, month):
    """Aggregate record values for an indicator over a given org unit + period."""
    from sqlalchemy import extract, func
    if not indicator.entity_field_id:
        return 0

    unit_ids = visible_unit_ids(current_user.id)
    q = db.session.query(func.sum(RecordValue.value_number)).join(
        Record, Record.id == RecordValue.record_id
    ).filter(
        Record.entity_type_id == indicator.entity_type_id,
        Record.org_unit_id == org_unit_id,
        Record.org_unit_id.in_(unit_ids),
        Record.is_active == True,
        RecordValue.entity_field_id == indicator.entity_field_id,
        extract('year', Record.created_at) == year,
        extract('month', Record.created_at) == month,
    )
    result = q.scalar()
    return float(result or 0)


@indicators_bp.route('/')
@login_required
def list_indicators():
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    program_id = request.args.get('program_id', type=int)
    sector = request.args.get('sector', '')

    q = Indicator.query.filter_by(org_id=current_user.org_id, is_active=True)
    if program_id:
        q = q.filter_by(program_id=program_id)
    if sector:
        q = q.filter_by(sector=sector)

    indicators = q.order_by(Indicator.sector, Indicator.name).all()
    programs = Program.query.filter_by(org_id=current_user.org_id, is_active=True).all()

    return render_template(
        'indicators/list.html',
        indicators=indicators,
        programs=programs,
        sectors=SECTORS,
        sel_program_id=program_id,
        sel_sector=sector,
    )


@indicators_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_indicator():
    from app.utils.role_access import can_access
    if not current_user.is_superadmin and not can_access('admin_section'):
        flash('Only admins can create indicators.', 'error')
        return redirect(url_for('indicators.list_indicators'))

    programs = Program.query.filter_by(org_id=current_user.org_id, is_active=True).all()
    entity_types = EntityType.query.filter_by(org_id=current_user.org_id, is_active=True).all()

    if request.method == 'POST':
        f = request.form
        ind = Indicator(
            org_id=current_user.org_id,
            program_id=f.get('program_id', type=int) or None,
            name=f.get('name', '').strip(),
            code=f.get('code', '').strip() or None,
            description=f.get('description', '').strip() or None,
            unit=f.get('unit', '').strip() or None,
            sector=f.get('sector') or None,
            aggregation=f.get('aggregation', 'sum'),
            target_type=f.get('target_type', 'cumulative'),
            entity_type_id=f.get('entity_type_id', type=int) or None,
            entity_field_id=f.get('entity_field_id', type=int) or None,
            created_by=current_user.id,
        )
        db.session.add(ind)
        db.session.commit()
        flash(f'Indicator "{ind.name}" created.', 'success')
        return redirect(url_for('indicators.indicator_detail', indicator_id=ind.id))

    return render_template(
        'indicators/new.html',
        programs=programs,
        entity_types=entity_types,
        sectors=SECTORS,
        aggregation_types=AGGREGATION_TYPES,
        target_types=TARGET_TYPES,
    )


@indicators_bp.route('/<int:indicator_id>')
@login_required
def indicator_detail(indicator_id):
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    ind = Indicator.query.filter_by(
        id=indicator_id, org_id=current_user.org_id
    ).first_or_404()

    now = datetime.utcnow()
    year = request.args.get('year', now.year, type=int)

    unit_ids = visible_unit_ids(current_user.id)
    units = OrgUnit.query.filter(OrgUnit.id.in_(unit_ids)).order_by(OrgUnit.name).all()

    monthly_data = []
    for month in range(1, 13):
        val = IndicatorValue.query.filter_by(
            indicator_id=ind.id, period_year=year, period_month=month
        ).first()
        computed = _compute_indicator_value(ind, None, year, month) if not val else None
        monthly_data.append({
            'month': month,
            'value': val.value if val else computed,
            'is_manual': val.is_manual if val else False,
        })

    targets = IndicatorTarget.query.filter_by(
        indicator_id=ind.id, period_year=year
    ).all()
    annual_target = sum(t.target_value for t in targets)

    return render_template(
        'indicators/detail.html',
        indicator=ind,
        year=year,
        monthly_data=monthly_data,
        annual_target=annual_target,
        targets=targets,
        units=units,
    )


@indicators_bp.route('/<int:indicator_id>/target', methods=['POST'])
@login_required
def set_target(indicator_id):
    from app.utils.role_access import can_access
    if not current_user.is_superadmin and not can_access('admin_section'):
        flash('Only admins can set targets.', 'error')
        return redirect(url_for('indicators.indicator_detail', indicator_id=indicator_id))

    ind = Indicator.query.filter_by(
        id=indicator_id, org_id=current_user.org_id
    ).first_or_404()

    f = request.form
    year = f.get('year', type=int)
    month = f.get('month', type=int) or None
    org_unit_id = f.get('org_unit_id', type=int) or None
    target_value = f.get('target_value', type=float)

    existing = IndicatorTarget.query.filter_by(
        indicator_id=ind.id, org_unit_id=org_unit_id,
        period_year=year, period_month=month
    ).first()
    if existing:
        existing.target_value = target_value
    else:
        t = IndicatorTarget(
            indicator_id=ind.id,
            org_unit_id=org_unit_id,
            period_year=year,
            period_month=month,
            target_value=target_value,
        )
        db.session.add(t)
    db.session.commit()
    flash('Target saved.', 'success')
    return redirect(url_for('indicators.indicator_detail', indicator_id=ind.id))


@indicators_bp.route('/api/fields/<int:entity_type_id>')
@login_required
def fields_for_type(entity_type_id):
    fields = EntityField.query.filter_by(
        entity_type_id=entity_type_id
    ).order_by(EntityField.order).all()
    return jsonify([{'id': f.id, 'label': f.label, 'field_type': f.field_type} for f in fields])
