from datetime import datetime, timedelta
import jwt
from flask import Blueprint, request, jsonify
from app.config import Config
from app.models.user import User
from app.extensions import bcrypt
from app.utils.decorators import api_auth
from flask import g

api_auth_bp = Blueprint('api_auth', __name__, url_prefix='/api/v1/auth')


def make_token(user_id, expires_days):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=expires_days),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')


@api_auth_bp.route('/token', methods=['POST'])
def token():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not user.is_active or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({'status': 'error', 'code': 'INVALID_CREDENTIALS',
                        'message': 'Invalid email or password'}), 401

    return jsonify({
        'status': 'ok',
        'data': {
            'access_token': make_token(user.id, 7),
            'refresh_token': make_token(user.id, 30),
            'token_type': 'Bearer',
        }
    })


@api_auth_bp.route('/refresh', methods=['POST'])
def refresh():
    data = request.get_json() or {}
    refresh_token = data.get('refresh_token', '')
    try:
        payload = jwt.decode(refresh_token, Config.SECRET_KEY, algorithms=['HS256'])
        user = User.query.get(payload['user_id'])
        if not user or not user.is_active:
            raise Exception()
    except Exception:
        return jsonify({'status': 'error', 'code': 'UNAUTHORIZED', 'message': 'Invalid refresh token'}), 401

    return jsonify({
        'status': 'ok',
        'data': {'access_token': make_token(user.id, 7), 'token_type': 'Bearer'}
    })


@api_auth_bp.route('/me')
@api_auth
def me():
    user = g.current_api_user
    assignments = [{'org_unit_id': a.org_unit_id, 'role': a.role} for a in user.unit_assignments]
    return jsonify({
        'status': 'ok',
        'data': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'org_id': user.org_id,
            'org': user.organisation.name if user.organisation else None,
            'is_superadmin': user.is_superadmin,
            'unit_assignments': assignments,
        }
    })
