from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.extensions import db, bcrypt
from app.models.user import User, UserOrgUnit
from app.models.org_unit import OrgUnit
from app.models.program import Program
from app.models.application import Application
from app.models.access import UserProgramAccess, UserApplicationAccess, PROGRAM_ROLES
from app.utils.decorators import require_role

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
@require_role('admin')
def index():
    return redirect(url_for('admin.users'))


@admin_bp.route('/users')
@login_required
@require_role('admin')
def users():
    org_users = User.query.filter_by(org_id=current_user.org_id).order_by(User.user_type, User.username).all()
    units = OrgUnit.query.filter_by(org_id=current_user.org_id, is_active=True).order_by(OrgUnit.level, OrgUnit.name).all()
    return render_template('admin/users.html', users=org_users, units=units)


@admin_bp.route('/users/new-web-user', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def new_web_user():
    units = OrgUnit.query.filter_by(org_id=current_user.org_id, is_active=True).order_by(OrgUnit.level, OrgUnit.name).all()
    programs = Program.query.filter_by(org_id=current_user.org_id, is_active=True).order_by(Program.name).all()

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip() or None
        last_name = request.form.get('last_name', '').strip() or None
        phone = request.form.get('phone', '').strip() or None
        role = request.form.get('role', 'data_entry')
        primary_unit_id = request.form.get('primary_unit_id') or None

        if not email or not username or not password:
            flash('Email, username, and password are required.', 'error')
            return render_template('admin/new_web_user.html', units=units, programs=programs,
                                   roles=UserOrgUnit.ROLES)

        if User.query.filter_by(email=email).first():
            flash('Email already in use.', 'error')
            return render_template('admin/new_web_user.html', units=units, programs=programs,
                                   roles=UserOrgUnit.ROLES)

        user = User(
            org_id=current_user.org_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            user_type='web_user',
            primary_org_unit_id=int(primary_unit_id) if primary_unit_id else None,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            is_active=True,
            is_superadmin=request.form.get('is_superadmin') == 'on',
        )
        db.session.add(user)
        db.session.flush()

        # Assign role to primary unit (or all units if none selected)
        unit_ids = request.form.getlist('unit_ids')
        if not unit_ids and primary_unit_id:
            unit_ids = [primary_unit_id]
        for uid in unit_ids:
            if role not in UserOrgUnit.ROLES:
                role = 'data_entry'
            db.session.add(UserOrgUnit(user_id=user.id, org_unit_id=int(uid), role=role))

        # Assign program spaces
        prog_ids = request.form.getlist('program_ids')
        for pid in prog_ids:
            prog_role = request.form.get(f'prog_role_{pid}', 'data_entry')
            if prog_role not in PROGRAM_ROLES:
                prog_role = 'data_entry'
            db.session.add(UserProgramAccess(
                user_id=user.id, program_id=int(pid),
                role_in_program=prog_role, granted_by=current_user.id, is_active=True,
            ))

        db.session.commit()
        flash(f'Web user "{username}" created.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/new_web_user.html', units=units, programs=programs,
                           roles=UserOrgUnit.ROLES)


@admin_bp.route('/users/new-mobile-worker', methods=['POST'])
@login_required
@require_role('admin')
def new_mobile_worker():
    email = request.form.get('email', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    first_name = request.form.get('first_name', '').strip() or None
    last_name = request.form.get('last_name', '').strip() or None
    primary_unit_id = request.form.get('primary_unit_id') or None

    if not username or not password:
        flash('Username and password are required.', 'error')
        return redirect(url_for('admin.users'))

    if not email:
        email = f'{username}@{current_user.org_id}.local'

    if User.query.filter_by(email=email).first():
        flash('Email already in use.', 'error')
        return redirect(url_for('admin.users'))

    user = User(
        org_id=current_user.org_id,
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        user_type='mobile_worker',
        primary_org_unit_id=int(primary_unit_id) if primary_unit_id else None,
        password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()

    if primary_unit_id:
        db.session.add(UserOrgUnit(user_id=user.id, org_unit_id=int(primary_unit_id), role='data_entry'))

    db.session.commit()
    flash(f'Mobile worker "{username}" created.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@require_role('admin')
def toggle_user(user_id):
    user = User.query.filter_by(id=user_id, org_id=current_user.org_id).first_or_404()
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'User {"activated" if user.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/units')
@login_required
@require_role('admin')
def user_units(user_id):
    user = User.query.filter_by(id=user_id, org_id=current_user.org_id).first_or_404()
    units = OrgUnit.query.filter_by(org_id=current_user.org_id, is_active=True).order_by(OrgUnit.level, OrgUnit.name).all()
    assignments = UserOrgUnit.query.filter_by(user_id=user.id).all()
    assigned_map = {a.org_unit_id: a for a in assignments}
    return render_template('admin/user_units.html', user=user, units=units,
                           assigned_map=assigned_map, roles=UserOrgUnit.ROLES)


@admin_bp.route('/users/<int:user_id>/units/save', methods=['POST'])
@login_required
@require_role('admin')
def save_user_units(user_id):
    user = User.query.filter_by(id=user_id, org_id=current_user.org_id).first_or_404()
    UserOrgUnit.query.filter_by(user_id=user.id).delete()

    unit_ids = request.form.getlist('unit_ids')
    for uid in unit_ids:
        role = request.form.get(f'role_{uid}', 'data_entry')
        if role not in UserOrgUnit.ROLES:
            role = 'data_entry'
        db.session.add(UserOrgUnit(user_id=user.id, org_unit_id=int(uid), role=role))

    db.session.commit()
    flash('Unit assignments saved.', 'success')
    return redirect(url_for('admin.user_units', user_id=user_id))


# ── Program Space access ───────────────────────────────────────────────────────

@admin_bp.route('/users/<int:user_id>/spaces')
@login_required
@require_role('admin')
def user_spaces(user_id):
    user = User.query.filter_by(id=user_id, org_id=current_user.org_id).first_or_404()
    programs = Program.query.filter_by(org_id=current_user.org_id, is_active=True).order_by(Program.name).all()
    applications = Application.query.filter_by(org_id=current_user.org_id, is_active=True).order_by(Application.name).all()

    prog_access = {a.program_id: a for a in
                   UserProgramAccess.query.filter_by(user_id=user.id, is_active=True).all()}
    app_access = {a.application_id: a for a in
                  UserApplicationAccess.query.filter_by(user_id=user.id, is_active=True).all()}

    return render_template(
        'admin/user_spaces.html',
        user=user,
        programs=programs,
        applications=applications,
        prog_access=prog_access,
        app_access=app_access,
        program_roles=PROGRAM_ROLES,
    )


@admin_bp.route('/users/<int:user_id>/spaces/save', methods=['POST'])
@login_required
@require_role('admin')
def save_user_spaces(user_id):
    user = User.query.filter_by(id=user_id, org_id=current_user.org_id).first_or_404()

    # --- Programs ---
    # Deactivate all existing, then re-grant checked ones
    UserProgramAccess.query.filter_by(user_id=user.id).delete()
    prog_ids = request.form.getlist('program_ids')
    for pid in prog_ids:
        role = request.form.get(f'prog_role_{pid}', 'data_entry')
        if role not in PROGRAM_ROLES:
            role = 'data_entry'
        db.session.add(UserProgramAccess(
            user_id=user.id,
            program_id=int(pid),
            role_in_program=role,
            granted_by=current_user.id,
            is_active=True,
        ))

    # --- Applications ---
    UserApplicationAccess.query.filter_by(user_id=user.id).delete()
    app_ids = request.form.getlist('application_ids')
    for aid in app_ids:
        can_submit = request.form.get(f'app_submit_{aid}') == 'on'
        can_view = request.form.get(f'app_view_{aid}') == 'on'
        db.session.add(UserApplicationAccess(
            user_id=user.id,
            application_id=int(aid),
            can_submit=can_submit,
            can_view=can_view,
            granted_by=current_user.id,
            is_active=True,
        ))

    db.session.commit()
    flash(f'Program and application spaces saved for {user.username}.', 'success')
    return redirect(url_for('admin.user_spaces', user_id=user_id))
