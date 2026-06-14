from flask import Blueprint, jsonify, session
from database.database import get_site_metrics, get_user_usage, get_user_usage_summary

import importlib

try:
    ai_memory = importlib.import_module('memory')
except ImportError:
    ai_memory = None

api_bp = Blueprint('api', __name__)


@api_bp.route('/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'OK',
        'service': 'Astravox-api',
        'version': '1.0.0',
        'timestamp': __import__('datetime').datetime.utcnow().isoformat() + 'Z'
    }), 200


@api_bp.route('/me', methods=['GET'])
def me():
    if session.get('user_id'):
        return jsonify({
            'status': 'OK',
            'user': {
                'id': session.get('user_id'),
                'username': session.get('username')
            }
        }), 200

    return jsonify({
        'status': 'OK',
        'user': None
    }), 200


@api_bp.route('/usage', methods=['GET'])
def usage():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'status': 'ERROR',
            'error': 'Authentication required.',
            'code': 'AUTH_REQUIRED'
        }), 401

    usage_data = get_user_usage(user_id)
    summary_data = get_user_usage_summary(user_id)
    return jsonify({
        'status': 'OK',
        'usage': usage_data,
        'summary': summary_data
    }), 200


@api_bp.route('/metrics', methods=['GET'])
def metrics():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'status': 'ERROR',
            'error': 'Authentication required.',
            'code': 'AUTH_REQUIRED'
        }), 401

    metrics_data = get_site_metrics()
    return jsonify({
        'status': 'OK',
        'metrics': metrics_data
    }), 200


@api_bp.route('/analytics', methods=['GET'])
def analytics():
    return metrics()


@api_bp.route('/conversations', methods=['GET'])
def conversations():
    if ai_memory and hasattr(ai_memory, 'list_conversations'):
        return jsonify({
            'status': 'OK',
            'conversations': ai_memory.list_conversations()
        }), 200

    return jsonify({
        'status': 'OK',
        'conversations': []
    }), 200
