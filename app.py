from flask import Flask, session

from routes.login import login_bp
from routes.register import register_bp
from routes.account import account_bp
from routes.product import product_bp
from routes.index import index_bp


app = Flask(
    __name__,
    template_folder='frontend',
    static_folder='frontend',
    static_url_path='/static'
)

app.secret_key = '123456789'

app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024


@app.context_processor
def inject_cart_count():
    cart = session.get('cart', {})

    cart_count = sum(
        int(quantity)
        for quantity in cart.values()
    )

    return {
        'cart_count': cart_count
    }


app.register_blueprint(login_bp)
app.register_blueprint(register_bp)
app.register_blueprint(account_bp)
app.register_blueprint(product_bp)
app.register_blueprint(index_bp)


if __name__ == '__main__':
    app.run(debug=True)