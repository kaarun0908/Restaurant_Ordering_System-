
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

ADMIN_EMAIL = "kaarun.t2024@vitstudent.ac.in".strip().lower()

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


# DATABASE CONNECTION

def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# CREATE DATABASE TABLES AND MIGRATE EXISTING DATABASE

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

        # Add payment columns without deleting existing orders.
        order_columns = {
            row["name"]
            for row in db.execute(
                "PRAGMA table_info(orders)"
            ).fetchall()
        }

        if "payment_method" not in order_columns:
            db.execute("""
                ALTER TABLE orders
                ADD COLUMN payment_method TEXT
                NOT NULL DEFAULT 'Cash on Delivery'
            """)

        if "payment_status" not in order_columns:
            db.execute("""
                ALTER TABLE orders
                ADD COLUMN payment_status TEXT
                NOT NULL DEFAULT 'Pending'
            """)

        # V3: Customer reviews and ratings.
        # Creates the table if it does not exist; existing data is preserved.
        db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                food_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, food_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)


# CUSTOMER LOGIN PROTECTION

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in before continuing.", "warning")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


# ADMIN LOGIN PROTECTION

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))

        if not session.get("is_admin"):
            abort(403)

        return view(*args, **kwargs)

    return wrapped


# COMMON TEMPLATE DATA

@app.context_processor
def shared_data():
    cart = session.get("cart", {})

    return {
        "current_user": session.get("user_name"),
        "cart_count": sum(int(q) for q in cart.values())
    }


# CART CALCULATION

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


# HOME PAGE

@app.route("/")
def home():
    return render_template("index.html", foods=FOODS)


# CUSTOMER REGISTRATION

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash(
                "Enter all details. Password must have at least 8 characters.",
                "danger"
            )
        else:
            try:
                with get_db() as db:
                    db.execute(
                        """INSERT INTO users(name, email, password)
                           VALUES (?, ?, ?)""",
                        (name, email, generate_password_hash(password))
                    )

                flash(
                    "Registration successful! Please log in.",
                    "success"
                )
                return redirect(url_for("login"))

            except sqlite3.IntegrityError:
                flash("This email is already registered.", "danger")

    return render_template("register.html")


# CUSTOMER AND ADMIN LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        login_type = request.form.get(
            "login_type", "customer"
        ).strip().lower()

        if login_type not in ("customer", "admin"):
            flash(
                "Please choose Customer Login or Admin Login.",
                "danger"
            )
            return render_template("login.html")

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

        if not user or not check_password_hash(
            user["password"], password
        ):
            flash("Incorrect email or password.", "danger")
            return render_template("login.html")

        is_admin_account = (
            bool(ADMIN_EMAIL)
            and user["email"].strip().lower() == ADMIN_EMAIL
        )

        if login_type == "admin" and not is_admin_account:
            flash(
                "This account is not authorized for Admin Login.",
                "danger"
            )
            return render_template("login.html")

        if login_type == "customer" and is_admin_account:
            flash(
                "Please select Admin Login for this account.",
                "warning"
            )
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["is_admin"] = (
            login_type == "admin" and is_admin_account
        )

        flash("Welcome back, " + user["name"] + "!", "success")

        if session["is_admin"]:
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("home"))

    return render_template("login.html")


# LOGOUT

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("home"))


# MENU WITH SEARCH, CATEGORY AND SORTING

@app.route("/menu")
def menu():
    category = request.args.get("category", "").strip()
    search = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "default")

    foods = [dict(food) for food in FOODS]

    # Add real customer review averages and counts to each food item.
    with get_db() as db:
        review_rows = db.execute("""
            SELECT food_id, AVG(rating) AS average_rating,
                   COUNT(*) AS review_count
            FROM reviews
            GROUP BY food_id
        """).fetchall()

    review_summary = {
        row["food_id"]: {
            "average_rating": round(float(row["average_rating"]), 1),
            "review_count": row["review_count"]
        }
        for row in review_rows
    }

    for food in foods:
        summary = review_summary.get(food["id"])
        if summary:
            food["average_rating"] = summary["average_rating"]
            food["review_count"] = summary["review_count"]
        else:
            # Keep the original sample rating until customers submit reviews.
            food["average_rating"] = food["rating"]
            food["review_count"] = 0

    if search:
        search_lower = search.lower()

        foods = [
            food for food in foods
            if search_lower in food["name"].lower()
            or search_lower in food["description"].lower()
        ]

    if category:
        foods = [
            food for food in foods
            if food["category"].lower() == category.lower()
        ]

    if sort_by == "price_low":
        foods.sort(key=lambda food: food["price"])

    elif sort_by == "price_high":
        foods.sort(
            key=lambda food: food["price"],
            reverse=True
        )

    elif sort_by == "rating":
        foods.sort(
            key=lambda food: food["average_rating"],
            reverse=True
        )

    return render_template(
        "menu.html",
        foods=foods,
        category=category,
        search=search,
        sort_by=sort_by
    )


# CUSTOMER REVIEWS AND RATINGS

@app.route("/food/<int:food_id>/reviews", methods=["GET", "POST"])
@login_required
def food_reviews(food_id):
    food = next(
        (item for item in FOODS if item["id"] == food_id),
        None
    )
    if food is None:
        abort(404)

    with get_db() as db:
        # A customer may review a food item only after ordering it.
        purchased = db.execute("""
            SELECT 1
            FROM orders
            JOIN order_items ON orders.id = order_items.order_id
            WHERE orders.user_id = ? AND order_items.food_name = ?
            LIMIT 1
        """, (session["user_id"], food["name"])).fetchone()

        if request.method == "POST":
            if not purchased:
                flash(
                    "You can review this food only after ordering it.",
                    "warning"
                )
                return redirect(url_for("food_reviews", food_id=food_id))

            try:
                rating = int(request.form.get("rating", "0"))
            except (TypeError, ValueError):
                rating = 0

            comment = request.form.get("comment", "").strip()

            if rating < 1 or rating > 5:
                flash("Please select a rating from 1 to 5.", "danger")
            elif not comment:
                flash("Please enter your review.", "danger")
            elif len(comment) > 1000:
                flash("Your review must be 1000 characters or fewer.", "danger")
            else:
                db.execute("""
                    INSERT INTO reviews (user_id, food_id, rating, comment)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, food_id)
                    DO UPDATE SET
                        rating = excluded.rating,
                        comment = excluded.comment,
                        created_at = CURRENT_TIMESTAMP
                """, (session["user_id"], food_id, rating, comment))
                flash("Your review has been saved!", "success")
                return redirect(url_for("food_reviews", food_id=food_id))

        existing_review = db.execute("""
            SELECT rating, comment
            FROM reviews
            WHERE user_id = ? AND food_id = ?
        """, (session["user_id"], food_id)).fetchone()

        reviews = db.execute("""
            SELECT reviews.rating, reviews.comment, reviews.created_at,
                   users.name AS customer_name
            FROM reviews
            JOIN users ON reviews.user_id = users.id
            WHERE reviews.food_id = ?
            ORDER BY reviews.created_at DESC, reviews.id DESC
        """, (food_id,)).fetchall()

        summary = db.execute("""
            SELECT AVG(rating) AS average_rating, COUNT(*) AS review_count
            FROM reviews
            WHERE food_id = ?
        """, (food_id,)).fetchone()

    average_rating = (
        round(float(summary["average_rating"]), 1)
        if summary["average_rating"] is not None
        else None
    )

    return render_template(
        "reviews.html",
        food=food,
        reviews=reviews,
        purchased=bool(purchased),
        existing_review=existing_review,
        average_rating=average_rating,
        review_count=summary["review_count"]
    )


# VIEW CART

@app.route("/cart")
def cart():
    items, total = get_cart()

    return render_template(
        "cart.html",
        items=items,
        total=total
    )


# ADD FOOD TO CART

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


# UPDATE CART QUANTITY

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


# CHECKOUT WITH CASH ON DELIVERY OR SIMULATED PAYMENT

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
        payment_method = request.form.get(
            "payment_method", "cod"
        ).strip().lower()

        if not name or not phone or not address:
            flash("Please fill in all delivery details.", "danger")
            return render_template(
                "checkout.html", items=items, total=total
            )

        if payment_method not in ("cod", "simulated"):
            flash("Please select a valid payment method.", "danger")
            return render_template(
                "checkout.html", items=items, total=total
            )

        if payment_method == "simulated":
            session["pending_payment"] = {
                "user_id": session["user_id"],
                "name": name,
                "phone": phone,
                "address": address,
            }

            return redirect(url_for("simulate_payment"))

        return create_food_order(
            name, phone, address, items,
            payment_method="Cash on Delivery",
            payment_status="Pending"
        )

    return render_template(
        "checkout.html", items=items, total=total
    )


# SAVE ORDER AND ORDER ITEMS

def create_food_order(
    name, phone, address, items,
    payment_method, payment_status
):
    total = sum(
        item["price"] * item["quantity"]
        for item in items
    )

    with get_db() as db:
        cursor = db.execute("""
            INSERT INTO orders (
                user_id, customer_name, phone, address, total,
                payment_method, payment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"], name, phone, address, total,
            payment_method, payment_status
        ))

        order_id = cursor.lastrowid

        for item in items:
            db.execute("""
                INSERT INTO order_items (
                    order_id, food_name, price, quantity
                )
                VALUES (?, ?, ?, ?)
            """, (
                order_id, item["name"],
                item["price"], item["quantity"]
            ))


    session["cart"] = {}
    session.pop("pending_payment", None)

    return redirect(
        url_for("order_success", order_id=order_id)
    )


# SIMULATED PAYMENT PAGE

@app.route("/simulate-payment", methods=["GET", "POST"])
@login_required
def simulate_payment():
    payment = session.get("pending_payment")

    if (
        not payment
        or payment.get("user_id") != session["user_id"]
    ):
        flash(
            "Please start checkout before making a payment.",
            "warning"
        )
        return redirect(url_for("checkout"))

    items, total = get_cart()

    if not items:
        session.pop("pending_payment", None)
        flash(
            "Your cart is empty. Please add items again.",
            "warning"
        )
        return redirect(url_for("menu"))

    if request.method == "POST":
        result = request.form.get("result", "")

        if result == "success":
            return create_food_order(
                payment["name"],
                payment["phone"],
                payment["address"],
                items,
                payment_method="Simulated Online Payment",
                payment_status="Paid (Simulated)"
            )

        if result == "failure":
            session.pop("pending_payment", None)
            return render_template(
                "payment_result.html",
                success=False
            )

        flash("Invalid payment selection.", "danger")

    return render_template(
        "payment.html",
        payment=payment,
        total=total
    )


# ORDER SUCCESS PAGE

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

    return render_template(
        "order_success.html",
        order=order,
        items=items
    )


# CUSTOMER ORDER HISTORY

@app.route("/order-history")
@login_required
def order_history():
    with get_db() as db:
        orders = db.execute(
            """
            SELECT * FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (session["user_id"],)
        ).fetchall()

        order_details = []

        for order in orders:
            items = db.execute(
                """
                SELECT food_name, price, quantity
                FROM order_items
                WHERE order_id = ?
                ORDER BY id
                """,
                (order["id"],)
            ).fetchall()

            order_details.append({
                "order": order,
                "items": items
            })

    return render_template(
        "order_history.html",
        order_details=order_details
    )


# ADMIN DASHBOARD AND REPORTS

@app.route("/admin")
@admin_required
def admin_dashboard():
    with get_db() as db:
        orders = db.execute("""
            SELECT
                orders.*,
                users.name AS account_name,
                users.email AS customer_email
            FROM orders
            JOIN users ON orders.user_id = users.id
            ORDER BY orders.created_at DESC, orders.id DESC
        """).fetchall()

        order_items = {}

        for order in orders:
            items = db.execute("""
                SELECT food_name, price, quantity
                FROM order_items
                WHERE order_id = ?
                ORDER BY id
            """, (order["id"],)).fetchall()

            order_items[order["id"]] = items

        # Main dashboard metrics
        total_orders = len(orders)
        total_revenue = sum(float(order["total"]) for order in orders)

        pending_orders = sum(
            1 for order in orders
            if order["status"] == "Order received"
        )

        total_customers = db.execute(
            "SELECT COUNT(*) FROM users WHERE LOWER(email) != LOWER(?)",
            (ADMIN_EMAIL,)
        ).fetchone()[0]

        # Count orders by status for the report summary.
        status_rows = db.execute("""
            SELECT COALESCE(status, 'Unknown') AS status,
                   COUNT(*) AS order_count
            FROM orders
            GROUP BY COALESCE(status, 'Unknown')
            ORDER BY order_count DESC, status
        """).fetchall()
        status_counts = [
            {"status": row["status"], "count": row["order_count"]}
            for row in status_rows
        ]

        # Most frequently ordered food items.
        popular_rows = db.execute("""
            SELECT food_name,
                   SUM(quantity) AS quantity_sold,
                   SUM(price * quantity) AS item_revenue
            FROM order_items
            GROUP BY food_name
            ORDER BY quantity_sold DESC, item_revenue DESC, food_name
            LIMIT 5
        """).fetchall()
        popular_items = [
            {
                "food_name": row["food_name"],
                "quantity_sold": row["quantity_sold"],
                "item_revenue": round(float(row["item_revenue"] or 0), 2)
            }
            for row in popular_rows
        ]

        # Revenue and order count for the last seven calendar days.
        daily_rows = db.execute("""
            SELECT DATE(created_at) AS sales_date,
                   COUNT(*) AS order_count,
                   SUM(total) AS revenue
            FROM orders
            WHERE DATE(created_at) >= DATE('now', '-6 days')
            GROUP BY DATE(created_at)
            ORDER BY sales_date
        """).fetchall()

        # Include dates with zero orders so the chart has a continuous range.
        daily_lookup = {
            row["sales_date"]: {
                "orders": row["order_count"],
                "revenue": round(float(row["revenue"] or 0), 2)
            }
            for row in daily_rows
        }
        daily_sales = []
        for offset in range(6, -1, -1):
            day_row = db.execute(
                "SELECT DATE('now', ?) AS sales_date",
                (f"-{offset} days",)
            ).fetchone()
            sales_date = day_row["sales_date"]
            values = daily_lookup.get(
                sales_date, {"orders": 0, "revenue": 0}
            )
            daily_sales.append({
                "date": sales_date,
                "orders": values["orders"],
                "revenue": values["revenue"]
            })

        review_stats = db.execute("""
            SELECT COUNT(*) AS review_count,
                   AVG(rating) AS average_rating
            FROM reviews
        """).fetchone()

        total_reviews = review_stats["review_count"]
        average_customer_rating = (
            round(float(review_stats["average_rating"]), 1)
            if review_stats["average_rating"] is not None
            else None
        )

    return render_template(
        "admin_dashboard.html",
        orders=orders,
        order_items=order_items,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        total_customers=total_customers,
        status_counts=status_counts,
        popular_items=popular_items,
        daily_sales=daily_sales,
        total_reviews=total_reviews,
        average_customer_rating=average_customer_rating
    )


# ACCESS DENIED ERROR

@app.errorhandler(403)
def forbidden(error):
    return (
        "<h1>403 - Access denied</h1>"
        "<p>Only the administrator can access this page.</p>"
        "<p><a href='/'>Return to Foodies</a></p>",
        403
    )


# PAGE NOT FOUND ERROR

@app.errorhandler(404)
def page_not_found(error):
    return (
        "<h1>404 - Page not found</h1>"
        "<p><a href='/'>Return to Foodies</a></p>",
        404
    )


# INITIALIZE DATABASE

init_db()


if __name__ == "__main__":
    app.run(debug=True)
