from decimal import Decimal

from db import get_db_connection


def get_cart(session):
    cart = session.get('cart', {})

    if not isinstance(cart, dict):
        cart = {}

    return cart


def add_product_to_cart(session, product_id):
    cart = get_cart(session)

    product_id = str(product_id)

    current_quantity = cart.get(product_id, 0)

    cart[product_id] = int(current_quantity) + 1

    session['cart'] = cart
    session.modified = True

    return cart


def update_cart_item(session, product_id, quantity):
    cart = get_cart(session)

    product_id = str(product_id)
    quantity = int(quantity)

    if quantity <= 0:
        cart.pop(product_id, None)
    else:
        cart[product_id] = quantity

    session['cart'] = cart
    session.modified = True

    return cart


def remove_product_from_cart(session, product_id):
    cart = get_cart(session)

    product_id = str(product_id)

    cart.pop(product_id, None)

    session['cart'] = cart
    session.modified = True

    return cart


def get_cart_context(session):
    cart = get_cart(session)

    if not cart:
        return {
            'cart_products': [],
            'grand_total': Decimal('0'),
            'cart_count': 0
        }

    product_ids = list(cart.keys())

    placeholders = ', '.join(['%s'] * len(product_ids))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT *
        FROM product
        WHERE id IN ({placeholders})
        """,
        product_ids
    )

    products = cursor.fetchall()

    cursor.close()
    conn.close()

    cart_products = []
    grand_total = Decimal('0')

    for product in products:
        product_id = str(product['id'])
        quantity = int(cart.get(product_id, 0))
        price = Decimal(str(product['price']))
        subtotal = price * quantity

        cart_products.append({
            'id': product['id'],
            'title': product['title'],
            'price': price,
            'image': product['image'],
            'quantity': quantity,
            'subtotal': subtotal
        })

        grand_total += subtotal

    return {
        'cart_products': cart_products,
        'grand_total': grand_total,
        'cart_count': sum(cart.values())
    }