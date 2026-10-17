
import os
import sqlite3
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FOODIES_SECRET_KEY", "foodies-v1-development-key"
)

DB_PATH = Path(__file__).with_name("foodies.db")

FOODS = [
    {
        "id": 1, "name": "Chicken Biryani",
        "category": "Biryani", "price": 189, "rating": 4.7,
        "description": "Aromatic basmati rice and tender chicken.",
        "image": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?auto=format&fit=crop&w=800&q=85"

    },
    {
        "id": 2, "name": "Margherita Pizza",
        "category": "Pizza", "price": 229, "rating": 4.5,
        "description": "Mozzarella, basil and tomato sauce.",
        "image": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=800&q=80"
    },
    {
        "id": 3, "name": "Masala Dosa",
        "category": "South Indian", "price": 99, "rating": 4.6,
        "description": "Crispy dosa served with chutney and sambar.",
        "image": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=800&q=80"
    },
    {
        "id": 4, "name": "Smash Burger",
        "category": "Burgers", "price": 169, "rating": 4.4,
        "description": "Grilled burger with fresh vegetables.",
        "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=800&q=80"
    },
    {
        "id": 5, "name": "Paneer Wrap",
        "category": "Wraps", "price": 139, "rating": 4.3,
        "description": "Spiced paneer wrapped with fresh vegetables.",
        "image": "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=800&q=80"
    },
    {
        "id": 6, "name": "Chilli Garlic Noodles",
        "category": "Chinese", "price": 159, "rating": 4.4,
        "description": "Wok-tossed noodles with garlic and vegetables.",
        "image": "https://images.unsplash.com/photo-1585032226651-759b368d7246?auto=format&fit=crop&w=800&q=80"
    },
    {
        "id": 7, "name": "Chocolate Brownie",
        "category": "Desserts", "price": 109, "rating": 4.8,
        "description": "Rich chocolate brownie with a soft centre.",
        "image": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=800&q=80"
    },
    {
        "id": 8, "name": "Crispy Chicken",
        "category": "Starters", "price": 199, "rating": 4.5,
        "description": "Crispy, seasoned chicken bites.",
        "image": "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?auto=format&fit=crop&w=800&q=80"
    }
]


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                total REAL NOT NULL,
                status TEXT DEFAULT 'Order received',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                food_name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id)
                    ON DELETE CASCADE
            )
        """)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in before placing an order.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def shared_data():
    cart = session.get("cart", {})
    return {
        "current_user": session.get("user_name"),
        "cart_count": sum(int(q) for q in cart.values())
    }


def get_cart():
    cart = session.get("cart", {})
    items = []
    total = 0

    for food in FOODS:
        quantity = int(cart.get(str(food["id"]), 0))
        if quantity > 0:
            item = dict(food)
            item["quantity"] = quantity
            item["subtotal"] = quantity * food["price"]
            items.append(item)
            total += item["subtotal"]

    return items, total


@app.route("/")
def home():
    return render_template("index.html", foods=FOODS)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash("Enter all details. Password must have at least 8 characters.", "danger")
        else:
            try:
                with get_db() as db:
                    db.execute(
                        "INSERT INTO users(name, email, password) VALUES (?, ?, ?)",
                        (name, email, generate_password_hash(password))
                    )
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for("login"))

            except sqlite3.IntegrityError:
                flash("This email is already registered.", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Welcome back, " + user["name"] + "!", "success")
            return redirect(url_for("home"))

        flash("Incorrect email or password.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("home"))


@app.route("/menu")
def menu():
    category = request.args.get("category", "")
    foods = [
        food for food in FOODS
        if not category or food["category"].lower() == category.lower()
    ]
    return render_template("menu.html", foods=foods, category=category)


@app.route("/cart")
def cart():
    items, total = get_cart()
    return render_template("cart.html", items=items, total=total)


@app.route("/cart/add/<int:food_id>", methods=["POST"])
def add_to_cart(food_id):
    if not any(food["id"] == food_id for food in FOODS):
        abort(404)

    cart = session.get("cart", {})
    key = str(food_id)
    cart[key] = min(int(cart.get(key, 0)) + 1, 20)
    session["cart"] = cart

    flash("Item added to your cart.", "success")
    return redirect(request.referrer or url_for("menu"))


@app.route("/cart/update/<int:food_id>", methods=["POST"])
def update_cart(food_id):
    cart = session.get("cart", {})

    try:
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        quantity = 1

    if quantity <= 0:
        cart.pop(str(food_id), None)
    else:
        cart[str(food_id)] = min(quantity, 20)

    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items, total = get_cart()

    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("menu"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not name or not phone or not address:
            flash("Please fill in all delivery details.", "danger")
        else:
            with get_db() as db:
                cursor = db.execute("""
                    INSERT INTO orders
                    (user_id, customer_name, phone, address, total)
                    VALUES (?, ?, ?, ?, ?)
                """, (session["user_id"], name, phone, address, total))

                order_id = cursor.lastrowid

                for item in items:
                    db.execute("""
                        INSERT INTO order_items
                        (order_id, food_name, price, quantity)
                        VALUES (?, ?, ?, ?)
                    """, (
                        order_id, item["name"],
                        item["price"], item["quantity"]
                    ))

            session["cart"] = {}
            return redirect(url_for("order_success", order_id=order_id))

    return render_template("checkout.html", items=items, total=total)


@app.route("/order-success/<int:order_id>")
@login_required
def order_success(order_id):
    with get_db() as db:
        order = db.execute(
            "SELECT * FROM orders WHERE id = ? AND user_id = ?",
            (order_id, session["user_id"])
        ).fetchone()

        if order is None:
            abort(404)

        items = db.execute(
            "SELECT * FROM order_items WHERE order_id = ?",
            (order_id,)
        ).fetchall()

    return render_template("order_success.html", order=order, items=items)


@app.errorhandler(404)
def page_not_found(error):
    return "<h1>404 - Page not found</h1><p><a href='/'>Return to Foodies</a></p>", 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
