import os
import uuid

from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    current_app,
    abort,
    jsonify
)

from werkzeug.utils import secure_filename

from db import get_db_connection

from routes.cart import (
    add_product_to_cart,
    get_cart,
    get_cart_context,
    remove_product_from_cart,
    update_cart_item,
)


product_bp = Blueprint('product', __name__)

ALLOWED_EXTENSIONS = {
    'png',
    'jpg',
    'jpeg',
    'gif',
    'webp'
}


def require_login():
    return 'user_id' in session


def allowed_file(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def calculate_cart_count(cart):
    cart_count = 0

    for quantity in cart.values():
        try:
            cart_count += int(quantity)
        except (TypeError, ValueError):
            continue

    return cart_count


def format_money(value):
    try:
        return f'{Decimal(str(value)):.2f}'
    except (InvalidOperation, TypeError, ValueError):
        return '0.00'


def save_image(image):
    if not image or not image.filename:
        return None

    if not allowed_file(image.filename):
        return None

    original_name = secure_filename(image.filename)
    extension = original_name.rsplit('.', 1)[1].lower()

    new_filename = f'{uuid.uuid4().hex}.{extension}'

    upload_folder = os.path.join(
        current_app.root_path,
        current_app.static_folder,
        'uploads',
        'products'
    )

    os.makedirs(upload_folder, exist_ok=True)

    image.save(
        os.path.join(
            upload_folder,
            new_filename
        )
    )

    return new_filename


@product_bp.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if not require_login():
        return jsonify({
            'success': False,
            'message': 'Bạn cần đăng nhập để thêm sản phẩm vào giỏ hàng.'
        }), 401

    data = request.get_json(silent=True) or {}
    product_id = data.get('id')

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return jsonify({
            'success': False,
            'message': 'ID sản phẩm không hợp lệ.'
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM product
        WHERE id = %s
        """,
        (product_id,)
    )

    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        return jsonify({
            'success': False,
            'message': 'Không tìm thấy sản phẩm.'
        }), 404

    cart = add_product_to_cart(
        session,
        product_id
    )

    return jsonify({
        'success': True,
        'message': 'Đã thêm vào giỏ hàng.',
        'cart_count': calculate_cart_count(cart)
    })


@product_bp.route('/cart/update', methods=['POST'])
def update_cart():
    if not require_login():
        return jsonify({
            'success': False,
            'message': 'Bạn cần đăng nhập để thay đổi giỏ hàng.'
        }), 401

    data = request.get_json(silent=True) or {}

    product_id = data.get('product_id')
    action = data.get('action')

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return jsonify({
            'success': False,
            'message': 'ID sản phẩm không hợp lệ.'
        }), 400

    if action not in {
        'increase',
        'decrease',
        'remove'
    }:
        return jsonify({
            'success': False,
            'message': 'Hành động không hợp lệ.'
        }), 400

    cart = get_cart(session)
    product_key = str(product_id)

    try:
        quantity = int(
            cart.get(product_key, 0)
        )
    except (TypeError, ValueError):
        quantity = 0

    if quantity <= 0:
        return jsonify({
            'success': False,
            'message': 'Sản phẩm không có trong giỏ hàng.'
        }), 404

    if action == 'increase':
        update_cart_item(
            session,
            product_id,
            quantity + 1
        )

    elif action == 'decrease':
        if quantity <= 1:
            return jsonify({
                'success': False,
                'message': 'Số lượng nhỏ nhất là 1.'
            }), 400

        update_cart_item(
            session,
            product_id,
            quantity - 1
        )

    elif action == 'remove':
        remove_product_from_cart(
            session,
            product_id
        )

    updated_cart = get_cart(session)
    cart_context = get_cart_context(session)

    updated_item = None

    for item in cart_context.get(
        'cart_products',
        []
    ):
        if str(item['id']) == str(product_id):
            updated_item = item
            break

    if updated_item:
        updated_quantity = int(
            updated_item['quantity']
        )

        updated_subtotal = format_money(
            updated_item['subtotal']
        )
    else:
        updated_quantity = 0
        updated_subtotal = '0.00'

    grand_total = cart_context.get(
        'grand_total',
        Decimal('0.00')
    )

    cart_count = calculate_cart_count(
        updated_cart
    )

    return jsonify({
        'success': True,
        'product_id': product_id,
        'action': action,
        'quantity': updated_quantity,
        'subtotal': updated_subtotal,
        'grand_total': format_money(grand_total),
        'cart_count': cart_count,
        'is_empty': cart_count == 0
    })


@product_bp.route('/cart')
@product_bp.route('/cart.html')
def cart():
    cart_context = get_cart_context(session)

    return render_template(
        'cart.html',
        **cart_context
    )


@product_bp.route('/my-product')
def my_product():
    if 'user_id' not in session:
        return redirect(
            url_for('login.login')
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM product
        WHERE id_user = %s
        ORDER BY id DESC
        """,
        (session['user_id'],)
    )

    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'my-product.html',
        products=products
    )


@product_bp.route(
    '/add-product',
    methods=['GET', 'POST']
)
def add_product():
    if 'user_id' not in session:
        return redirect(
            url_for('login.login')
        )

    errors = {}
    title = ''
    price = ''

    if request.method == 'POST':
        title = request.form.get(
            'title',
            ''
        ).strip()

        price = request.form.get(
            'price',
            ''
        ).strip()

        image = request.files.get('image')

        if not title:
            errors['title'] = 'Title is required.'

        if not price:
            errors['price'] = 'Price is required.'
        else:
            try:
                price_value = Decimal(price)

                if price_value <= 0:
                    errors['price'] = (
                        'Price must be greater than 0.'
                    )

            except InvalidOperation:
                errors['price'] = (
                    'Price must be a number.'
                )

        if not image or not image.filename:
            errors['image'] = 'Image is required.'

        elif not allowed_file(image.filename):
            errors['image'] = (
                'Only PNG, JPG, JPEG, GIF and WEBP are allowed.'
            )

        if not errors:
            image_name = save_image(image)

            if not image_name:
                errors['image'] = (
                    'Unable to save image.'
                )

        if not errors:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO product
                    (title, price, image, id_user)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    title,
                    price_value,
                    image_name,
                    session['user_id']
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

            return redirect(
                url_for('product.my_product')
            )

    return render_template(
        'add-product.html',
        errors=errors,
        title=title,
        price=price
    )


@product_bp.route(
    '/edit-product/<int:id>',
    methods=['GET', 'POST']
)
def edit_product(id):
    if 'user_id' not in session:
        return redirect(
            url_for('login.login')
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM product
        WHERE id = %s
        AND id_user = %s
        """,
        (
            id,
            session['user_id']
        )
    )

    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()

        abort(404)

    errors = {}

    if request.method == 'POST':
        title = request.form.get(
            'title',
            ''
        ).strip()

        price = request.form.get(
            'price',
            ''
        ).strip()

        image = request.files.get('image')

        if not title:
            errors['title'] = 'Title is required.'

        if not price:
            errors['price'] = 'Price is required.'
        else:
            try:
                price_value = Decimal(price)

                if price_value <= 0:
                    errors['price'] = (
                        'Price must be greater than 0.'
                    )

            except InvalidOperation:
                errors['price'] = (
                    'Price must be a number.'
                )

        if image and image.filename:
            if not allowed_file(image.filename):
                errors['image'] = (
                    'Only PNG, JPG, JPEG, GIF and WEBP are allowed.'
                )

        if not errors:
            image_name = product['image']

            if image and image.filename:
                new_image_name = save_image(image)

                if new_image_name:
                    image_name = new_image_name
                else:
                    errors['image'] = (
                        'Unable to save image.'
                    )

        if not errors:
            cursor.execute(
                """
                UPDATE product
                SET title = %s,
                    price = %s,
                    image = %s
                WHERE id = %s
                AND id_user = %s
                """,
                (
                    title,
                    price_value,
                    image_name,
                    id,
                    session['user_id']
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

            return redirect(
                url_for('product.my_product')
            )

        product['title'] = title
        product['price'] = price

    cursor.close()
    conn.close()

    return render_template(
        'edit-product.html',
        product=product,
        errors=errors
    )


@product_bp.route(
    '/delete-product/<int:id>',
    methods=['POST']
)
def delete_product(id):
    if 'user_id' not in session:
        return redirect(
            url_for('login.login')
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM product
        WHERE id = %s
        AND id_user = %s
        """,
        (
            id,
            session['user_id']
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for('product.my_product')
    )