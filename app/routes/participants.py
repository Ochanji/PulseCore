from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.participant import Participant, Household, ProgramEnrollment, GENDERS, CONSENT_STATUSES
from app.models.org_unit import OrgUnit
from app.models.program import Program
from app.models.audit import log_action
from app.utils.visibility import visible_unit_ids
from datetime import date
import uuid

participants_bp = Blueprint('participants', __name__, url_prefix='/participants')


def _require_access():
    from app.utils.role_access import can_access
    if not current_user.is_superadmin and not can_access('participants'):
        flash('Access denied.', 'error')
        return False
    return True


def _visible_units():
    ids = visible_unit_ids(current_user.id)
    return OrgUnit.query.filter(OrgUnit.id.in_(ids)).order_by(OrgUnit.name).all()


@participants_bp.route('/')
@login_required
def list_participants():
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    from app.utils.visibility import visible_program_ids
    unit_ids = visible_unit_ids(current_user.id)
    prog_ids = visible_program_ids(current_user)

    # Participants enrolled in accessible programs, or unaffiliated (no enrollment)
    from app.models.participant import ProgramEnrollment as PE
    enrolled_in_scope = db.session.query(PE.participant_id).filter(
        PE.program_id.in_(prog_ids)
    ).subquery()

    q = Participant.query.filter(
        Participant.org_id == current_user.org_id,
        Participant.is_active == True,
        db.or_(
            Participant.id.in_(enrolled_in_scope),
            ~Participant.enrollments.any(),  # unaffiliated participants visible to all
        )
    )

    search = request.args.get('q', '').strip()
    if search:
        q = q.filter(
            db.or_(
                Participant.first_name.ilike(f'%{search}%'),
                Participant.last_name.ilike(f'%{search}%'),
                Participant.national_id.ilike(f'%{search}%'),
                Participant.case_number.ilike(f'%{search}%'),
            )
        )

    org_unit_id = request.args.get('org_unit_id', type=int)
    if org_unit_id:
        q = q.filter(Participant.org_unit_id == org_unit_id)
    else:
        q = q.filter(Participant.org_unit_id.in_(unit_ids))

    consent = request.args.get('consent', '')
    if consent:
        q = q.filter(Participant.consent_status == consent)

    participants = q.order_by(Participant.created_at.desc()).limit(200).all()
    total = q.count()

    return render_template(
        'participants/list.html',
        participants=participants,
        total=total,
        visible_units=_visible_units(),
        genders=GENDERS,
        consent_statuses=CONSENT_STATUSES,
        sel_search=search,
        sel_org_unit_id=org_unit_id,
        sel_consent=consent,
    )


@participants_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    programs = Program.query.filter_by(org_id=current_user.org_id, is_active=True).all()

    if request.method == 'POST':
        f = request.form
        case_number = f'P-{str(uuid.uuid4())[:8].upper()}'

        p = Participant(
            org_id=current_user.org_id,
            org_unit_id=f.get('org_unit_id') or None,
            registered_by=current_user.id,
            first_name=f.get('first_name', '').strip(),
            last_name=f.get('last_name', '').strip() or None,
            date_of_birth=f.get('date_of_birth') or None,
            gender=f.get('gender') or None,
            national_id=f.get('national_id', '').strip() or None,
            phone=f.get('phone', '').strip() or None,
            case_number=case_number,
            consent_status=f.get('consent_status', 'pending'),
            consent_date=f.get('consent_date') or None,
            notes=f.get('notes', '').strip() or None,
        )
        db.session.add(p)
        db.session.flush()

        program_id = f.get('program_id', type=int)
        if program_id:
            enrollment = ProgramEnrollment(
                participant_id=p.id,
                program_id=program_id,
                org_unit_id=p.org_unit_id,
                enrolled_by=current_user.id,
                status='active',
            )
            db.session.add(enrollment)

        db.session.commit()
        log_action('create', 'Participant', p.id, f'Registered {p.full_name}')
        db.session.commit()

        flash(f'Participant {p.full_name} registered — case number {case_number}', 'success')
        return redirect(url_for('participants.profile', participant_id=p.id))

    return render_template(
        'participants/register.html',
        visible_units=_visible_units(),
        programs=programs,
        genders=GENDERS,
        consent_statuses=CONSENT_STATUSES,
    )


@participants_bp.route('/<int:participant_id>')
@login_required
def profile(participant_id):
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    p = Participant.query.filter_by(
        id=participant_id, org_id=current_user.org_id
    ).first_or_404()

    enrollments = p.enrollments.order_by(ProgramEnrollment.enrolled_at.desc()).all()
    records = p.records.limit(20).all()

    return render_template(
        'participants/profile.html',
        participant=p,
        enrollments=enrollments,
        records=records,
    )


@participants_bp.route('/<int:participant_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(participant_id):
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    p = Participant.query.filter_by(
        id=participant_id, org_id=current_user.org_id
    ).first_or_404()

    if request.method == 'POST':
        f = request.form
        p.first_name = f.get('first_name', '').strip()
        p.last_name = f.get('last_name', '').strip() or None
        p.date_of_birth = f.get('date_of_birth') or None
        p.gender = f.get('gender') or None
        p.national_id = f.get('national_id', '').strip() or None
        p.phone = f.get('phone', '').strip() or None
        p.org_unit_id = f.get('org_unit_id') or None
        p.consent_status = f.get('consent_status', p.consent_status)
        p.consent_date = f.get('consent_date') or p.consent_date
        p.notes = f.get('notes', '').strip() or None
        db.session.commit()
        log_action('update', 'Participant', p.id, f'Updated {p.full_name}')
        db.session.commit()
        flash('Participant updated.', 'success')
        return redirect(url_for('participants.profile', participant_id=p.id))

    return render_template(
        'participants/edit.html',
        participant=p,
        visible_units=_visible_units(),
        genders=GENDERS,
        consent_statuses=CONSENT_STATUSES,
    )


@participants_bp.route('/<int:participant_id>/enroll', methods=['POST'])
@login_required
def enroll(participant_id):
    if not _require_access():
        return redirect(url_for('dashboard.index'))

    p = Participant.query.filter_by(
        id=participant_id, org_id=current_user.org_id
    ).first_or_404()

    program_id = request.form.get('program_id', type=int)
    if not program_id:
        flash('Select a program.', 'error')
        return redirect(url_for('participants.profile', participant_id=p.id))

    existing = ProgramEnrollment.query.filter_by(
        participant_id=p.id, program_id=program_id
    ).first()
    if existing:
        flash('Already enrolled in that program.', 'error')
        return redirect(url_for('participants.profile', participant_id=p.id))

    enroll = ProgramEnrollment(
        participant_id=p.id,
        program_id=program_id,
        org_unit_id=p.org_unit_id,
        enrolled_by=current_user.id,
        status='active',
    )
    db.session.add(enroll)
    db.session.commit()
    flash('Participant enrolled in program.', 'success')
    return redirect(url_for('participants.profile', participant_id=p.id))


@participants_bp.route('/<int:participant_id>/deactivate', methods=['POST'])
@login_required
def deactivate(participant_id):
    from app.utils.role_access import can_access
    if not current_user.is_superadmin and not can_access('admin_section'):
        flash('Access denied.', 'error')
        return redirect(url_for('participants.list_participants'))

    p = Participant.query.filter_by(
        id=participant_id, org_id=current_user.org_id
    ).first_or_404()
    p.is_active = False
    db.session.commit()
    log_action('delete', 'Participant', p.id, f'Deactivated {p.full_name}')
    db.session.commit()
    flash(f'{p.full_name} deactivated.', 'success')
    return redirect(url_for('participants.list_participants'))
