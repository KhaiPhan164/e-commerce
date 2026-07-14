import re

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session
)

from werkzeug.security import generate_password_hash
from db import get_db_connection


account_bp = Blueprint('account', __name__)


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None


@account_bp.route('/account', methods=['GET', 'POST'])
def account():

    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    errors = {}
    success = ''

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM `user` WHERE id = %s",
        (session['user_id'],)
    )

    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()

        session.clear()

        return redirect(url_for('login.login'))

    if request.method == 'POST':

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user['name'] = name
        user['email'] = email

        if not name:
            errors['name'] = 'Name is required.'

        if not email:
            errors['email'] = 'Email is required.'
        elif not is_valid_email(email):
            errors['email'] = 'Invalid email format.'

        if not errors:
            cursor.execute(
                """
                SELECT id
                FROM `user`
                WHERE email = %s
                AND id != %s
                """,
                (email, session['user_id'])
            )

            email_exists = cursor.fetchone()

            if email_exists:
                errors['email'] = 'Email already exists.'

        if not errors:

            if password:
                password_hash = generate_password_hash(password)

                cursor.execute(
                    """
                    UPDATE `user`
                    SET name = %s,
                        email = %s,
                        password = %s
                    WHERE id = %s
                    """,
                    (
                        name,
                        email,
                        password_hash,
                        session['user_id']
                    )
                )

            else:
                cursor.execute(
                    """
                    UPDATE `user`
                    SET name = %s,
                        email = %s
                    WHERE id = %s
                    """,
                    (
                        name,
                        email,
                        session['user_id']
                    )
                )

            conn.commit()

            session['user_name'] = name
            session['user_email'] = email

            success = 'Update account successfully.'

            cursor.execute(
                "SELECT * FROM `user` WHERE id = %s",
                (session['user_id'],)
            )

            user = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'account.html',
        user=user,
        errors=errors,
        success=success
    )


@account_bp.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('login.login'))