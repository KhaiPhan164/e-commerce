import re

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session
)

from werkzeug.security import check_password_hash
from db import get_db_connection


login_bp = Blueprint('login', __name__)


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None


@login_bp.route('/login', methods=['GET', 'POST'])
def login():

    errors = {}
    email = ''
    user = None

    if request.method == 'POST':

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email:
            errors['email'] = 'Email is required.'

        elif not is_valid_email(email):
            errors['email'] = 'Invalid email format.'

        if not password:
            errors['password'] = 'Password is required.'

        if not errors:

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM `user` WHERE email = %s",
                (email,)
            )

            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user and check_password_hash(
                user['password'],
                password
            ):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']

                return redirect(url_for('account.account'))

            else:
                errors['login'] = (
                    'Email hoặc mật khẩu không chính xác.'
                )

    return render_template(
        'login.html',
        login_errors=errors,
        login_email=email
    )


@login_bp.route('/account')
def account():

    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM `user` WHERE id = %s",
        (session['user_id'],)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        session.clear()
        return redirect(url_for('login.login'))

    return render_template(
        'account.html',
        user=user,
        errors={},
        success=''
    )

@login_bp.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('login.login'))