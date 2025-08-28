"""Authentication and authorization for Vigint API"""

import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from vigint.models import db, APIKey, Client


def generate_api_key():
    """Generate a new API key"""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key):
    """Hash an API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key_hash):
    """Verify an API key and return the associated client"""
    api_key_record = APIKey.query.filter_by(
        key_hash=api_key_hash,
        is_active=True
    ).first()
    
    if api_key_record:
        return api_key_record.client
    return None


def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key in headers
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            # Check for API key in query parameters
            api_key = request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # Hash the provided API key
        api_key_hash = hash_api_key(api_key)
        
        # Verify the API key
        client = verify_api_key(api_key_hash)
        if not client:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Add client to request context
        request.current_client = client
        request.current_api_key = APIKey.query.filter_by(key_hash=api_key_hash).first()
        
        return f(*args, **kwargs)
    
    return decorated_function


def generate_jwt_token(client_id, expires_in_hours=24):
    """Generate a JWT token for a client"""
    payload = {
        'client_id': client_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow()
    }
    
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def verify_jwt_token(token):
    """Verify a JWT token and return the client"""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        client_id = payload['client_id']
        client = Client.query.get(client_id)
        return client
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_jwt_token(f):
    """Decorator to require JWT token authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for JWT token in headers
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'JWT token required'}), 401
        
        token = auth_header.split(' ')[1]
        client = verify_jwt_token(token)
        
        if not client:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add client to request context
        request.current_client = client
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_api_key_from_request():
    """Extract API key from request headers (supports both formats)"""
    # Check Authorization header (Bearer format)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    # Check X-API-Key header
    return request.headers.get('X-API-Key')


def require_api_key_flexible(f):
    """Flexible API key decorator that supports both header formats"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        
        api_key = get_api_key_from_request()
        if not api_key:
            api_key = request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # Hash the provided API key
        api_key_hash = hash_api_key(api_key)
        
        # Verify the API key
        client = verify_api_key(api_key_hash)
        if not client:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Add client to request context
        request.current_client = client
        from vigint.models import APIKey
        request.current_api_key = APIKey.query.filter_by(key_hash=api_key_hash).first()
        
        return f(*args, **kwargs)
    
    return decorated_function


def create_client_with_api_key(name, email):
    """Create a new client with an API key"""
    # Check if client already exists
    existing_client = Client.query.filter_by(email=email).first()
    if existing_client:
        raise ValueError(f"Client with email {email} already exists")
    
    # Create new client
    client = Client(name=name, email=email)
    db.session.add(client)
    db.session.flush()  # Get the client ID
    
    # Generate API key
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    # Create API key record
    api_key_record = APIKey(
        client_id=client.id,
        key_hash=api_key_hash,
        name=f"Default API Key for {name}"
    )
    db.session.add(api_key_record)
    db.session.commit()
    
    return client, api_key


def revoke_api_key(api_key_id):
    """Revoke an API key"""
    api_key_record = APIKey.query.get(api_key_id)
    if api_key_record:
        api_key_record.is_active = False
        db.session.commit()
        return True
    return False


def list_client_api_keys(client_id):
    """List all API keys for a client"""
    return APIKey.query.filter_by(client_id=client_id).all()