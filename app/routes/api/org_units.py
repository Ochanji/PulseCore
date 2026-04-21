from flask import Blueprint, jsonify, g
from app.models.org_unit import OrgUnit
from app.utils.decorators import api_auth
from app.utils.serialisers import org_unit_to_dict

api_org_units_bp = Blueprint('api_org_units', __name__, url_prefix='/api/v1/org-units')


@api_org_units_bp.route('/')
@api_auth
def list_org_units():
    user = g.current_api_user
    roots = OrgUnit.query.filter_by(
        org_id=user.org_id, parent_id=None, is_active=True
    ).all()
    tree = [org_unit_to_dict(r, include_children=True) for r in roots]
    return jsonify({'status': 'ok', 'data': tree})
