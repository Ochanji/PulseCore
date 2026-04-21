from flask import Blueprint, jsonify
from app.utils.decorators import api_auth

api_sync_bp = Blueprint('api_sync', __name__, url_prefix='/api/v1/sync')


@api_sync_bp.route('/push', methods=['POST'])
@api_auth
def push():
    return jsonify({
        'status': 'not_implemented',
        'message': 'Mobile sync coming in next phase.'
    }), 501


@api_sync_bp.route('/pull')
@api_auth
def pull():
    return jsonify({
        'status': 'not_implemented',
        'message': 'Mobile sync coming in next phase.'
    }), 501
