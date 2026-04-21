SECTION_ROLES = {
    'applications':   ['admin', 'supervisor', 'district_manager', 'data_entry', 'report_viewer'],
    'app_builder':    ['admin'],
    'records':        ['admin', 'supervisor', 'district_manager', 'read_only'],
    'entity_builder': ['admin'],
    'form_builder':   ['admin'],
    'reports':        ['admin', 'supervisor', 'district_manager', 'report_viewer'],
    'admin_section':  ['admin'],
    # IRC-scale sections
    'participants':   ['admin', 'supervisor', 'district_manager', 'data_entry'],
    'programs':       ['admin', 'supervisor', 'district_manager'],
    'workflow':       ['admin', 'supervisor', 'district_manager'],
    'indicators':     ['admin', 'supervisor', 'district_manager', 'report_viewer'],
}

# Sections a program admin can access (scoped to their programs)
PROGRAM_ADMIN_SECTIONS = {'app_builder', 'applications', 'admin_section', 'programs',
                          'participants', 'workflow', 'reports', 'indicators'}


def _is_program_admin(user):
    from app.models.access import UserProgramAccess
    return UserProgramAccess.query.filter_by(
        user_id=user.id, role_in_program='manager', is_active=True
    ).count() > 0


def can_access(section):
    from flask_login import current_user
    if not current_user or not current_user.is_authenticated:
        return False
    if current_user.is_superadmin:
        return True
    user_roles = [a.role for a in current_user.unit_assignments]
    if any(r in SECTION_ROLES.get(section, []) for r in user_roles):
        return True
    # Program admins get access to their scoped sections
    if section in PROGRAM_ADMIN_SECTIONS and _is_program_admin(current_user):
        return True
    return False


def is_data_entry_only():
    from flask_login import current_user
    if not current_user or not current_user.is_authenticated:
        return False
    if current_user.is_superadmin:
        return False
    user_roles = set(a.role for a in current_user.unit_assignments)
    return bool(user_roles) and user_roles <= {'data_entry'}


def is_report_viewer_only():
    from flask_login import current_user
    if not current_user or not current_user.is_authenticated:
        return False
    if current_user.is_superadmin:
        return False
    user_roles = set(a.role for a in current_user.unit_assignments)
    return bool(user_roles) and user_roles <= {'report_viewer'}
