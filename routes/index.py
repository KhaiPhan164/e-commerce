from flask import Blueprint, render_template

from db import get_db_connection


index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM `product`
        ORDER BY id DESC
        """
    )
    products = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('index.html', products=products)
