from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.program import Program, Grant, SECTORS
from app.models.audit import log_action

programs_bp = Blueprint('programs', __name__, url_prefix='/programs')


def _require_access():
    from app.utils.role_access import can_access
    if not current_user.is_superadmin and not can_access('programs'):
        flash('Access denied.', 'error')
        return False
    return True


@programs_bp.route('/')
@login_required
def list_programs():
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    programs = Program.query.filter_by(
        org_id=current_user.org_id, is_active=True
    ).order_by(Program.name).all()

    return render_template('programs/list.html', programs=programs, sectors=SECTORS)


@programs_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_program():
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        f = request.form
        prog = Program(
            org_id=current_user.org_id,
            name=f.get('name', '').strip(),
            code=f.get('code', '').strip() or None,
            sector=f.get('sector') or None,
            description=f.get('description', '').strip() or None,
            start_date=f.get('start_date') or None,
            end_date=f.get('end_date') or None,
            created_by=current_user.id,
        )
        db.session.add(prog)
        db.session.commit()
        log_action('create', 'Program', prog.id, prog.name)
        db.session.commit()
        flash(f'Program "{prog.name}" created.', 'success')
        return redirect(url_for('programs.program_detail', program_id=prog.id))

    return render_template('programs/new.html', sectors=SECTORS)


@programs_bp.route('/<int:program_id>')
@login_required
def program_detail(program_id):
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    prog = Program.query.filter_by(
        id=program_id, org_id=current_user.org_id
    ).first_or_404()
    grants = prog.grants.filter_by(is_active=True).order_by(Grant.name).all()

    return render_template('programs/detail.html', program=prog, grants=grants)


@programs_bp.route('/<int:program_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_program(program_id):
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    prog = Program.query.filter_by(
        id=program_id, org_id=current_user.org_id
    ).first_or_404()

    if request.method == 'POST':
        f = request.form
        prog.name = f.get('name', '').strip()
        prog.code = f.get('code', '').strip() or None
        prog.sector = f.get('sector') or None
        prog.description = f.get('description', '').strip() or None
        prog.start_date = f.get('start_date') or None
        prog.end_date = f.get('end_date') or None
        db.session.commit()
        flash('Program updated.', 'success')
        return redirect(url_for('programs.program_detail', program_id=prog.id))

    return render_template('programs/edit.html', program=prog, sectors=SECTORS)


@programs_bp.route('/<int:program_id>/grants/new', methods=['POST'])
@login_required
def new_grant(program_id):
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    prog = Program.query.filter_by(
        id=program_id, org_id=current_user.org_id
    ).first_or_404()

    f = request.form
    grant = Grant(
        program_id=prog.id,
        org_id=current_user.org_id,
        name=f.get('name', '').strip(),
        grant_code=f.get('grant_code', '').strip() or None,
        donor=f.get('donor', '').strip() or None,
        budget=f.get('budget', type=float),
        currency=f.get('currency', 'USD'),
        start_date=f.get('start_date') or None,
        end_date=f.get('end_date') or None,
        notes=f.get('notes', '').strip() or None,
    )
    db.session.add(grant)
    db.session.commit()
    flash(f'Grant "{grant.name}" added.', 'success')
    return redirect(url_for('programs.program_detail', program_id=prog.id))


@programs_bp.route('/grants/<int:grant_id>/delete', methods=['POST'])
@login_required
def delete_grant(grant_id):
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    grant = Grant.query.filter_by(id=grant_id, org_id=current_user.org_id).first_or_404()
    program_id = grant.program_id
    grant.is_active = False
    db.session.commit()
    flash('Grant removed.', 'success')
    return redirect(url_for('programs.program_detail', program_id=program_id))
