import os
from flask import Blueprint, current_app, send_from_directory

page_bp = Blueprint('page', __name__)


@page_bp.route('/')
def index():
    return send_from_directory(current_app.static_folder, 'index.html')


@page_bp.route('/<path:path>')
def static_proxy(path):
    root = current_app.static_folder
    if path.startswith('..'):
        return send_from_directory(root, 'index.html')
    full_path = os.path.join(root, path)
    if os.path.exists(full_path):
        return send_from_directory(root, path)
    return send_from_directory(root, 'index.html')
