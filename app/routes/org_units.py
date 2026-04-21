from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.org_unit import OrgUnit, OrgUnitLevel
from app.utils.decorators import require_role

org_units_bp = Blueprint('org_units', __name__, url_prefix='/admin/org-units')


def build_tree(units, parent_id=None):
    children = [u for u in units if u.parent_id == parent_id]
    result = []
    for u in children:
        result.append({'unit': u, 'children': build_tree(units, u.id)})
    return result


@org_units_bp.route('/')
@login_required
@require_role('admin')
def index():
    units = OrgUnit.query.filter_by(org_id=current_user.org_id, is_active=True).order_by(OrgUnit.level, OrgUnit.name).all()
    levels = OrgUnitLevel.query.filter_by(org_id=current_user.org_id).order_by(OrgUnitLevel.level).all()
    tree = build_tree(units)
    return render_template('org_units/index.html', tree=tree, units=units, levels=levels)


@org_units_bp.route('/levels', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def levels():
    if request.method == 'POST':
        level_num = request.form.get('level')
        name = request.form.get('name', '').strip()
        if level_num and name:
            existing = OrgUnitLevel.query.filter_by(org_id=current_user.org_id, level=int(level_num)).first()
            if existing:
                existing.name = name
            else:
                db.session.add(OrgUnitLevel(org_id=current_user.org_id, level=int(level_num), name=name))
            db.session.commit()
            flash('Level saved.', 'success')
        return redirect(url_for('org_units.levels'))

    org_levels = OrgUnitLevel.query.filter_by(org_id=current_user.org_id).order_by(OrgUnitLevel.level).all()
    return render_template('org_units/levels.html', levels=org_levels)


@org_units_bp.route('/new', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def create():
    units = OrgUnit.query.filter_by(org_id=current_user.org_id, is_active=True).order_by(OrgUnit.level, OrgUnit.name).all()
    levels = OrgUnitLevel.query.filter_by(org_id=current_user.org_id).order_by(OrgUnitLevel.level).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        parent_id = request.form.get('parent_id') or None
        code = request.form.get('code', '').strip() or None

        if not name:
            flash('Name is required.', 'error')
            return render_template('org_units/create.html', units=units, levels=levels, prefill_parent_id=None)

        parent = OrgUnit.query.get(int(parent_id)) if parent_id else None
        level = (parent.level + 1) if parent else 0
        parent_path = parent.path if parent else '/'

        unit = OrgUnit(
            org_id=current_user.org_id,
            parent_id=parent.id if parent else None,
            name=name,
            code=code,
            level=level,
            path=parent_path,
            is_active=True
        )
        db.session.add(unit)
        db.session.flush()
        unit.path = parent_path + str(unit.id) + '/'
        db.session.commit()
        flash(f'Org unit "{name}" created.', 'success')
        return redirect(url_for('org_units.index'))

    prefill_parent_id = request.args.get('parent_id', type=int)
    return render_template('org_units/create.html', units=units, levels=levels, prefill_parent_id=prefill_parent_id)


@org_units_bp.route('/<int:unit_id>/edit', methods=['POST'])
@login_required
@require_role('admin')
def edit(unit_id):
    unit = OrgUnit.query.filter_by(id=unit_id, org_id=current_user.org_id).first_or_404()
    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip() or None
    if name:
        unit.name = name
        unit.code = code
        db.session.commit()
        flash(f'"{name}" updated.', 'success')
    else:
        flash('Name is required.', 'error')
    return redirect(url_for('org_units.index'))


@org_units_bp.route('/<int:unit_id>/deactivate', methods=['POST'])
@login_required
@require_role('admin')
def deactivate(unit_id):
    unit = OrgUnit.query.filter_by(id=unit_id, org_id=current_user.org_id).first_or_404()
    unit.is_active = False
    db.session.commit()
    flash(f'"{unit.name}" archived.', 'success')
    return redirect(url_for('org_units.index'))


@org_units_bp.route('/<int:unit_id>/delete', methods=['POST'])
@login_required
@require_role('admin')
def delete(unit_id):
    unit = OrgUnit.query.filter_by(id=unit_id, org_id=current_user.org_id).first_or_404()
    has_children = OrgUnit.query.filter_by(parent_id=unit.id, is_active=True).count()
    if has_children:
        flash(f'Cannot delete "{unit.name}" — it has child units. Archive or remove children first.', 'error')
        return redirect(url_for('org_units.index'))
    name = unit.name
    db.session.delete(unit)
    db.session.commit()
    flash(f'"{name}" deleted.', 'success')
    return redirect(url_for('org_units.index'))
