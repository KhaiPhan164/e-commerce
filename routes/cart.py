from decimal import Decimal

from db import get_db_connection


def get_cart(session_obj):
    cart = session_obj.get('cart', {})
    if not isinstance(cart, dict):
        cart = {}
    return cart


def add_product_to_cart(session_obj, product_id):
    cart = get_cart(session_obj)
    key = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    session_obj['cart'] = cart
    return cart


def update_cart_item(session_obj, product_id, quantity):
    cart = get_cart(session_obj)
    key = str(product_id)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 0

    if quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = quantity

    session_obj['cart'] = cart
    return cart


def remove_product_from_cart(session_obj, product_id):
    cart = get_cart(session_obj)
    cart.pop(str(product_id), None)
    session_obj['cart'] = cart
    return cart


def get_cart_context(session_obj):
    cart = get_cart(session_obj)
    cart_products = []
    cart_total = Decimal('0')
    cart_quantity = 0

    product_ids = [int(pid) for pid in cart.keys() if str(pid).isdigit()]

    if product_ids:
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholder = ','.join(['%s'] * len(product_ids))
        cursor.execute(
            f"SELECT * FROM `product` WHERE id IN ({placeholder})",
            tuple(product_ids)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        products_by_id = {row['id']: row for row in rows}

        for pid in sorted(product_ids):
            product = products_by_id.get(pid)
            if not product:
                continue

            quantity = cart.get(str(pid), 0)
            subtotal = product['price'] * quantity
            cart_total += subtotal
            cart_quantity += quantity
            cart_products.append({
                'id': product['id'],
                'title': product['title'],
                'price': product['price'],
                'image': product.get('image'),
                'quantity': quantity,
                'subtotal': subtotal,
            })

    shipping_cost = Decimal('0') if cart_total >= Decimal('100') else Decimal('5')
    tax = (cart_total * Decimal('0.08')).quantize(Decimal('0.01'))
    grand_total = (cart_total + shipping_cost + tax).quantize(Decimal('0.01'))

    return {
        'cart_products': cart_products,
        'cart_total': cart_total,
        'cart_quantity': cart_quantity,
        'shipping_cost': shipping_cost,
        'tax': tax,
        'grand_total': grand_total,
    }
