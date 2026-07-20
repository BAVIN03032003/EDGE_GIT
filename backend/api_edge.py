from flask import request, jsonify

import mysql

import jwt

import datetime

import secrets

import hashlib
 
SECRET_KEY = '31c3286043bd35376b0397d43a211ff0e6fe37dd4d5786aa5c619f5b3fa323df'
 
 
# ── Helper: get tenant_id from JWT token ─────────────────────

def get_tenant_from_token():

    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):

        return None, jsonify({'error': 'Missing or invalid token'}), 401
 
    token = auth_header.split(' ')[1]

    try:

        payload   = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

        tenant_id = payload.get('tenant_id')

        if not tenant_id:

            return None, jsonify({'error': 'tenant_id missing in token'}), 401

        return tenant_id, None, None

    except jwt.ExpiredSignatureError:

        return None, jsonify({'error': 'Token expired. Please login again.'}), 401

    except jwt.InvalidTokenError:

        return None, jsonify({'error': 'Invalid token'}), 401
 
 
# ── Helper: generate API key pair ────────────────────────────

def generate_api_key():

    plain_key = f"sk_{secrets.token_bytes(32).hex()}"

    key_hash  = hashlib.sha256(plain_key.encode()).hexdigest()

    return plain_key, key_hash
 
 
# ─────────────────────────────────────────────────────────────

# GET /api/edges/

# List all edges for this tenant

# ─────────────────────────────────────────────────────────────

def get_edges():

    try:

        tenant_id, err, code = get_tenant_from_token()

        if err:

            return err, code
 
        cur = mysql.connection.cursor()

        cur.execute("""

            SELECT

                e.id,

                e.edge_name,

                e.location,

                e.is_online,

                e.last_seen,

                e.created_at,

                ak.created_at    AS key_created_at,

                ak.last_used_at  AS key_last_used,

                COUNT(DISTINCT d.id) AS device_count

            FROM edges e

            LEFT JOIN api_keys ak

                   ON ak.edge_id   = e.id

                  AND ak.is_active = 1

                  AND ak.tenant_id = e.tenant_id

            LEFT JOIN devices d

                   ON d.edge_id   = e.id

                  AND d.is_active = 1

            WHERE e.tenant_id = %s

              AND e.is_active  = 1

            GROUP BY

                e.id,

                e.edge_name,

                e.location,

                e.is_online,

                e.last_seen,

                e.created_at,

                ak.created_at,

                ak.last_used_at

            ORDER BY e.created_at DESC

        """, (tenant_id,))
 
        rows = cur.fetchall()

        cur.close()
 
        return jsonify({

            'success': True,

            'edges':   rows,

            'count':   len(rows)

        }), 200
 
    except Exception as e:

        return jsonify({'error': str(e)}), 500
 
 
# ─────────────────────────────────────────────────────────────

# POST /api/edges/

# Create new edge + generate API key

# ─────────────────────────────────────────────────────────────

def create_edge():

    try:

        tenant_id, err, code = get_tenant_from_token()

        if err:

            return err, code
 
        data      = request.json

        edge_name = data.get('edge_name', '').strip()

        location  = data.get('location',  '').strip()
 
        if not edge_name:

            return jsonify({'error': 'edge_name is required'}), 400
 
        cur = mysql.connection.cursor()
 
        # ── Create edge record ────────────────────────────

        cur.execute("""

            INSERT INTO edges

                (tenant_id, edge_name, location)

            VALUES

                (%s, %s, %s)

        """, (tenant_id, edge_name, location))
 
        edge_id = cur.lastrowid
 
        # ── Generate API key ──────────────────────────────

        plain_key, key_hash = generate_api_key()
 
        cur.execute("""

            INSERT INTO api_keys

                (tenant_id, edge_id, key_hash)

            VALUES

                (%s, %s, %s)

        """, (tenant_id, edge_id, key_hash))
 
        mysql.connection.commit()

        cur.close()
 
        return jsonify({

            'success':   True,

            'edge_id':   edge_id,

            'edge_name': edge_name,

            'location':  location,

            'api_key':   plain_key,

            'message':   'Copy this API key now. It will never be shown again.'

        }), 201
 
    except Exception as e:

        return jsonify({'error': str(e)}), 500
 
 
# ─────────────────────────────────────────────────────────────

# POST /api/edges/<edge_id>/regenerate-key/

# Deactivate old key and generate a new one

# ─────────────────────────────────────────────────────────────

def regenerate_key(edge_id):

    try:

        tenant_id, err, code = get_tenant_from_token()

        if err:

            return err, code
 
        cur = mysql.connection.cursor()
 
        # Verify edge belongs to this tenant

        cur.execute("""

            SELECT id FROM edges

            WHERE id        = %s

              AND tenant_id = %s

              AND is_active = 1

        """, (edge_id, tenant_id))
 
        edge = cur.fetchone()

        if not edge:

            cur.close()

            return jsonify({'error': 'Edge not found'}), 404
 
        # Deactivate all old keys for this edge

        cur.execute("""

            UPDATE api_keys

            SET    is_active = 0

            WHERE  edge_id   = %s

              AND  tenant_id = %s

        """, (edge_id, tenant_id))
 
        # Generate and store new key

        plain_key, key_hash = generate_api_key()
 
        cur.execute("""

            INSERT INTO api_keys

                (tenant_id, edge_id, key_hash)

            VALUES

                (%s, %s, %s)

        """, (tenant_id, edge_id, key_hash))
 
        mysql.connection.commit()

        cur.close()
 
        return jsonify({

            'success': True,

            'api_key': plain_key,

            'message': 'New key generated. Previous key is now deactivated.'

        }), 200
 
    except Exception as e:

        return jsonify({'error': str(e)}), 500
 
 
# ─────────────────────────────────────────────────────────────

# DELETE /api/edges/<edge_id>/

# Soft delete edge and deactivate its API key

# ─────────────────────────────────────────────────────────────

def delete_edge(edge_id):

    try:

        tenant_id, err, code = get_tenant_from_token()

        if err:

            return err, code
 
        cur = mysql.connection.cursor()
 
        # Verify edge belongs to this tenant

        cur.execute("""

            SELECT id FROM edges

            WHERE id        = %s

              AND tenant_id = %s

              AND is_active = 1

        """, (edge_id, tenant_id))
 
        edge = cur.fetchone()

        if not edge:

            cur.close()

            return jsonify({'error': 'Edge not found'}), 404
 
        # Soft delete edge

        cur.execute("""

            UPDATE edges

            SET    is_active = 0

            WHERE  id        = %s

              AND  tenant_id = %s

        """, (edge_id, tenant_id))
 
        # Deactivate API key

        cur.execute("""

            UPDATE api_keys

            SET    is_active = 0

            WHERE  edge_id   = %s

              AND  tenant_id = %s

        """, (edge_id, tenant_id))
 
        mysql.connection.commit()

        cur.close()
 
        return jsonify({

            'success': True,

            'message': 'Edge deleted successfully'

        }), 200
 
    except Exception as e:

        return jsonify({'error': str(e)}), 500
 
 
# ─────────────────────────────────────────────────────────────

# GET /api/edges/<edge_id>/

# Get single edge detail

# ─────────────────────────────────────────────────────────────

def get_edge(edge_id):

    try:

        tenant_id, err, code = get_tenant_from_token()

        if err:

            return err, code
 
        cur = mysql.connection.cursor()

        cur.execute("""

            SELECT

                e.id,

                e.edge_name,

                e.location,

                e.is_online,

                e.last_seen,

                e.created_at,

                ak.created_at   AS key_created_at,

                ak.last_used_at AS key_last_used,

                COUNT(DISTINCT d.id) AS device_count

            FROM edges e

            LEFT JOIN api_keys ak

                   ON ak.edge_id   = e.id

                  AND ak.is_active = 1

            LEFT JOIN devices d

                   ON d.edge_id   = e.id

                  AND d.is_active = 1

            WHERE e.id        = %s

              AND e.tenant_id = %s

              AND e.is_active = 1

            GROUP BY

                e.id, e.edge_name, e.location,

                e.is_online, e.last_seen, e.created_at,

                ak.created_at, ak.last_used_at

        """, (edge_id, tenant_id))
 
        edge = cur.fetchone()

        cur.close()
 
        if not edge:

            return jsonify({'error': 'Edge not found'}), 404
 
        return jsonify({

            'success': True,

            'edge':    edge

        }), 200
 
    except Exception as e:

        return jsonify({'error': str(e)}), 500
 