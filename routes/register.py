import os
import uuid
import hashlib
from werkzeug.security import generate_password_hash
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from db import get_db_connection

register_bp = Blueprint('register', __name__)

@register_bp.route('/register', methods=['GET', 'POST'])
def register():
    errors = {}
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()
        if not email:
            errors['email'] = 'Nhập email là bắt buộc.'
        if not password:
            errors['password'] = 'Nhập mật khẩu là bắt buộc.'
        if not name:
            errors['name'] = 'Nhập tên là bắt buộc.'
        if not errors:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("select id from `user` where email = %s", (email,))

            user = cursor.fetchone()
            if user:
                errors['email'] = 'Email đã tồn tại.'
                cursor.close()
                conn.close()
            else:
                hashed_password = generate_password_hash(password)
                cursor.execute("insert into `user` (email, password, name) values (%s, %s, %s)", (email, hashed_password, name))
                conn.commit()
                cursor.close()
                conn.close()
        if not errors:
            return redirect(url_for('login.login'))
    return render_template('login.html', errors=errors, email = email, name = name)