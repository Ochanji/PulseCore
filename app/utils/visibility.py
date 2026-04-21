from app.models.org_unit import OrgUnit
from app.models.user import UserOrgUnit


def visible_unit_ids(user_id):
    assignments = UserOrgUnit.query.filter_by(user_id=user_id).all()
    ids = set()
    for a in assignments:
        unit = OrgUnit.query.get(a.org_unit_id)
        if unit:
            matches = OrgUnit.query.filter(
                OrgUnit.path.like(unit.path + '%'),
                OrgUnit.is_active == True
            ).all()
            ids.update(u.id for u in matches)
    return list(ids)


def visible_program_ids(user):
    """
    Returns program IDs the user may access.

    Superadmins and org-level admins see all programs.
    All others are limited to programs explicitly granted via UserProgramAccess.
    If a user has no program grants at all, they fall back to seeing all programs
    (backwards-compatible for orgs that haven't configured program spaces yet).
    """
    if user.is_superadmin:
        from app.models.program import Program
        return [p.id for p in Program.query.filter_by(
            org_id=user.org_id, is_active=True).all()]

    user_roles = {a.role for a in user.unit_assignments}
    if 'admin' in user_roles:
        from app.models.program import Program
        return [p.id for p in Program.query.filter_by(
            org_id=user.org_id, is_active=True).all()]

    from app.models.access import UserProgramAccess
    grants = UserProgramAccess.query.filter_by(
        user_id=user.id, is_active=True
    ).all()

    if not grants:
        # No program spaces configured yet — fallback: all programs visible
        from app.models.program import Program
        return [p.id for p in Program.query.filter_by(
            org_id=user.org_id, is_active=True).all()]

    return [g.program_id for g in grants]


def visible_app_ids(user):
    """
    Returns application IDs the user may access.

    Superadmins and org admins see all apps.
    Others are limited to apps explicitly granted via UserApplicationAccess.
    Falls back to all apps if no grants are configured (backwards compatible).
    """
    if user.is_superadmin:
        from app.models.application import Application
        return [a.id for a in Application.query.filter_by(
            org_id=user.org_id, is_active=True).all()]

    user_roles = {a.role for a in user.unit_assignments}
    if 'admin' in user_roles:
        from app.models.application import Application
        return [a.id for a in Application.query.filter_by(
            org_id=user.org_id, is_active=True).all()]

    from app.models.access import UserApplicationAccess
    grants = UserApplicationAccess.query.filter_by(
        user_id=user.id, is_active=True
    ).all()

    if not grants:
        # No app-level grants configured yet — fallback: all apps visible
        from app.models.application import Application
        return [a.id for a in Application.query.filter_by(
            org_id=user.org_id, is_active=True).all()]

    return [g.application_id for g in grants]


def user_can_submit_app(user, application_id):
    """Check if user has submit permission for a specific application."""
    if user.is_superadmin:
        return True
    user_roles = {a.role for a in user.unit_assignments}
    if 'admin' in user_roles:
        return True
    from app.models.access import UserApplicationAccess
    grant = UserApplicationAccess.query.filter_by(
        user_id=user.id, application_id=application_id, is_active=True
    ).first()
    if not grant:
        # No explicit grant: allow if no grants exist at all (backwards compat)
        total = UserApplicationAccess.query.filter_by(
            user_id=user.id, is_active=True
        ).count()
        return total == 0
    return grant.can_submit


def get_user_role_at_unit(user_id, org_unit_id):
    unit = OrgUnit.query.get(org_unit_id)
    if not unit:
        return None
    ancestor_ids = [int(x) for x in unit.path.strip('/').split('/') if x]
    role_rank = {'admin': 0, 'supervisor': 1, 'data_entry': 2, 'read_only': 3}
    assignments = UserOrgUnit.query.filter(
        UserOrgUnit.user_id == user_id,
        UserOrgUnit.org_unit_id.in_(ancestor_ids + [org_unit_id])
    ).all()
    if not assignments:
        return None
    return min(assignments, key=lambda a: role_rank.get(a.role, 99)).role
