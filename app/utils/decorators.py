from functools import wraps
from flask import jsonify, redirect, url_for, g, request
from flask_login import current_user


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.is_superadmin:
                return f(*args, **kwargs)
            user_roles = [a.role for a in current_user.unit_assignments]
            if not any(r in roles for r in user_roles):
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def api_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        import jwt
        from app.config import Config
        from app.models.user import User

        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'status': 'error', 'code': 'UNAUTHORIZED', 'message': 'Token required'}), 401
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            user = User.query.get(payload['user_id'])
            if not user or not user.is_active:
                raise Exception('Invalid user')
            g.current_api_user = user
        except Exception:
            return jsonify({'status': 'error', 'code': 'UNAUTHORIZED', 'message': 'Invalid or expired token'}), 401
        return f(*args, **kwargs)
    return wrapper
