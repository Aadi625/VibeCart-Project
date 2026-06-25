from flask import Flask, render_template, request, redirect, url_for, session,flash
from database import get_db_connection

app = Flask(__name__)
app.secret_key = "ecommerce_secret_key"


# -----------------------------
# HOME
# -----------------------------
@app.route('/')
def home():
    return redirect(url_for('login'))


# -----------------------------
# REGISTER
# -----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO Users(name,email,password)
            VALUES(%s,%s,%s)
            """,
            (name, email, password)
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')


# -----------------------------
# LOGIN
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT * FROM Users
            WHERE email=%s AND password=%s
            """,
            (email, password)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user['user_id']
            session['name'] = user['name']

            return redirect(url_for('products'))

        return "Invalid Email or Password"

    return render_template('login.html')


# -----------------------------
# LOGOUT
# -----------------------------
@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('login'))


# -----------------------------
# PRODUCTS PAGE
# -----------------------------
@app.route('/products')
def products():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        cursor.execute(
            """
            SELECT *
            FROM Products
            WHERE product_name LIKE %s
            """,
            ('%' + search + '%',)
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM Products
            """
        )

    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'products.html',
        products=products,
        username=session['name'],
        search=search
    )

# -----------------------------
# ADD PRODUCT (ADMIN)
# -----------------------------
@app.route('/add_product', methods=['POST'])
def add_product():

    name = request.form['name']
    price = request.form['price']
    stock = request.form['stock']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO Products
        (product_name,price,stock)
        VALUES(%s,%s,%s)
        """,
        (name, price, stock)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('products'))


# -----------------------------
# ADD TO CART
# -----------------------------
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if item already exists in cart
    cursor.execute(
        """
        SELECT * FROM Cart
        WHERE user_id=%s AND product_id=%s
        """,
        (user_id, product_id)
    )

    item = cursor.fetchone()

    # Get available stock
    cursor.execute(
        """
        SELECT stock
        FROM Products
        WHERE product_id=%s
        """,
        (product_id,)
    )

    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return "Product not found."

    stock = product['stock']

    current_quantity = item['quantity'] if item else 0

    # Prevent adding more than available stock
    if current_quantity + 1 > stock:
        cursor.close()
        conn.close()
        flash("Cannot add more items. Stock limit reached.")
        return redirect(url_for('products'))

    if item:

        cursor.execute(
            """
            UPDATE Cart
            SET quantity = quantity + 1
            WHERE cart_id=%s
            """,
            (item['cart_id'],)
        )

    else:

        cursor.execute(
            """
            INSERT INTO Cart(user_id, product_id, quantity)
            VALUES(%s, %s, 1)
            """,
            (user_id, product_id)
        )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('products'))


# -----------------------------
# VIEW CART
# -----------------------------
@app.route('/cart')
def cart():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            Cart.cart_id,
            Products.product_name,
            Products.price,
            Cart.quantity,
            (Products.price * Cart.quantity) AS subtotal

        FROM Cart

        JOIN Products
        ON Cart.product_id = Products.product_id

        WHERE Cart.user_id=%s
        """,
        (user_id,)
    )

    cart_items = cursor.fetchall()

    total = sum(item['subtotal'] for item in cart_items)

    cursor.close()
    conn.close()

    return render_template(
        'cart.html',
        cart_items=cart_items,
        total=total
    )


# -----------------------------
# REMOVE FROM CART
# -----------------------------
@app.route('/remove_cart/<int:cart_id>')
def remove_cart(cart_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM Cart
        WHERE cart_id=%s
        """,
        (cart_id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('cart'))


# -----------------------------
# PLACE ORDER
# -----------------------------
@app.route('/place_order')
def place_order():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get all cart items
    cursor.execute(
        """
        SELECT
            Cart.product_id,
            Cart.quantity,
            Products.price,
            Products.product_name,
            Products.stock

        FROM Cart

        JOIN Products
        ON Cart.product_id = Products.product_id

        WHERE Cart.user_id = %s
        """,
        (user_id,)
    )

    items = cursor.fetchall()

    if not items:
        cursor.close()
        conn.close()
        return "Cart is Empty"

    # Check stock availability before placing order
    for item in items:

        if item['quantity'] > item['stock']:

            cursor.close()
            conn.close()

            return (
                f"Order failed. "
                f"{item['product_name']} has only "
                f"{item['stock']} items in stock."
            )

    # Calculate total amount
    total_amount = sum(
        item['price'] * item['quantity']
        for item in items
    )

    # Create order
    cursor.execute(
        """
        INSERT INTO Orders
        (user_id, total_amount, status)
        VALUES (%s, %s, 'Pending')
        """,
        (user_id, total_amount)
    )

    order_id = cursor.lastrowid

    # Save order details and reduce stock
    for item in items:

        cursor.execute(
            """
            INSERT INTO Order_Details
            (order_id, product_id, quantity, price)
            VALUES (%s, %s, %s, %s)
            """,
            (
                order_id,
                item['product_id'],
                item['quantity'],
                item['price']
            )
        )

        # Reduce stock
        cursor.execute(
            """
            UPDATE Products
            SET stock = stock - %s
            WHERE product_id = %s
            """,
            (
                item['quantity'],
                item['product_id']
            )
        )

    # Clear cart
    cursor.execute(
        """
        DELETE FROM Cart
        WHERE user_id = %s
        """,
        (user_id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('orders'))

# -----------------------------
# ORDER DETAILS
# -----------------------------

@app.route('/order_details/<int:order_id>')
def order_details(order_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            Products.product_name,
            Order_Details.quantity,
            Order_Details.price,
            (Order_Details.quantity * Order_Details.price) AS subtotal

        FROM Order_Details

        JOIN Products
        ON Order_Details.product_id = Products.product_id

        WHERE Order_Details.order_id = %s
        """,
        (order_id,)
    )

    items = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'order_details.html',
        items=items,
        order_id=order_id
    )

# -----------------------------
# ORDER HISTORY
# -----------------------------
@app.route('/orders')
def orders():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM Orders
        WHERE user_id=%s
        ORDER BY order_date DESC
        """,
        (user_id,)
    )

    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'orders.html',
        orders=orders
    )


# -----------------------------
# RUN APP
# -----------------------------
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)