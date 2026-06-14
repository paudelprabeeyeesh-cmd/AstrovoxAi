from flask import Blueprint, request, jsonify, session
from database.database import (
    create_user,
    verify_user_credentials,
    get_user_by_username_or_email,
    update_user_last_login,
)

auth_bp = Blueprint('auth', __name__)


def _create_session(user_row):
    session.clear()
    session.permanent = True
    session['user_id'] = str(user_row['id'])
    session['username'] = user_row['username']
    return {
        'user_id': session['user_id'],
        'username': session['username']
    }


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', '')).strip()

    if not username or not email or not password:
        return jsonify({
            'status': 'ERROR',
            'error': 'username, email, and password are required.',
            'code': 'MISSING_FIELDS'
        }), 400

    try:
        user_id = create_user(username, email, password)
        user = get_user_by_username_or_email(email)
        update_user_last_login(user['id'])
        session_data = _create_session(user)
        return jsonify({
            'status': 'OK',
            'message': 'Registration successful.',
            'user': {'id': user_id, 'username': username},
            'session': session_data
        }), 201
    except ValueError as err:
        return jsonify({
            'status': 'ERROR',
            'error': str(err),
            'code': 'USER_EXISTS'
        }), 400
    except Exception as err:
        return jsonify({
            'status': 'ERROR',
            'error': 'Unable to create account at this time.',
            'detail': str(err),
            'code': 'REGISTRATION_FAILED'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    identifier = str(data.get('username') or data.get('email') or '').strip()
    password = str(data.get('password', '')).strip()

    if not identifier or not password:
        return jsonify({
            'status': 'ERROR',
            'error': 'Username or email and password are required.',
            'code': 'MISSING_FIELDS'
        }), 400

    user = verify_user_credentials(identifier, password)
    if not user:
        return jsonify({
            'status': 'ERROR',
            'error': 'Invalid credentials.',
            'code': 'AUTH_FAILED'
        }), 401

    update_user_last_login(user['id'])
    session_data = _create_session(user)
    return jsonify({
        'status': 'OK',
        'message': 'Login successful.',
        'user': {'id': user['id'], 'username': user['username']},
        'session': session_data
    }), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    if session.get('user_id'):
        username = session.get('username')
        session.clear()
        return jsonify({
            'status': 'OK',
            'message': f'User {username} logged out successfully.'
        }), 200

    return jsonify({
        'status': 'ERROR',
        'error': 'No active session found.',
        'code': 'NO_SESSION'
    }), 400


@auth_bp.route('/status', methods=['GET'])
def status():
    if session.get('user_id'):
        return jsonify({
            'status': 'OK',
            'authenticated': True,
            'user': {
                'id': session.get('user_id'),
                'username': session.get('username')
            }
        }), 200

    return jsonify({
        'status': 'OK',
        'authenticated': False,
        'user': None
    }), 200
