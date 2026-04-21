from flask import Blueprint, jsonify, g
from app.models.entity import EntityType
from app.utils.decorators import api_auth
from app.utils.serialisers import entity_type_to_dict

api_entities_bp = Blueprint('api_entities', __name__, url_prefix='/api/v1/entities')


@api_entities_bp.route('/')
@api_auth
def list_entities():
    user = g.current_api_user
    entity_types = EntityType.query.filter_by(org_id=user.org_id, is_active=True).all()
    return jsonify({
        'status': 'ok',
        'data': [entity_type_to_dict(et) for et in entity_types],
        'meta': {'total': len(entity_types)}
    })


@api_entities_bp.route('/<int:entity_type_id>')
@api_auth
def get_entity(entity_type_id):
    user = g.current_api_user
    et = EntityType.query.filter_by(id=entity_type_id, org_id=user.org_id, is_active=True).first()
    if not et:
        return jsonify({'status': 'error', 'code': 'NOT_FOUND', 'message': 'Entity type not found'}), 404
    return jsonify({'status': 'ok', 'data': entity_type_to_dict(et)})
