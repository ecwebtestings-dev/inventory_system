
import os
import re
from functools import wraps
from flask import (
    Flask,
    session,
    redirect,
    url_for,
    request,
    render_template,
    jsonify,
    flash
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from MySQLdb import IntegrityError

from config import Config
from extensions import mysql


# Database functions


def create_user(full_name, email, password):
    cursor = mysql.connection.cursor()

    try:
        hashed_password = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (full_name, email, hashed_password)
        )

        mysql.connection.commit()
        return cursor.lastrowid

    except Exception:
        mysql.connection.rollback()
        raise

    finally:
        cursor.close()


def get_user_by_email(email):
    cursor = mysql.connection.cursor()

    try:
        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        return cursor.fetchone()

    finally:
        cursor.close()


def verify_user(email, password):
    user = get_user_by_email(email)

    if user and check_password_hash(user["password_hash"], password):
        return user

    return None


def product_summary():
    cursor = mysql.connection.cursor()

    try:
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                COALESCE(
                    SUM(quantity_in_stock <= reorder_level), 0
                ) AS low,
                COALESCE(
                    SUM(unit_price * quantity_in_stock), 0
                ) AS value
            FROM product
        """)

        return cursor.fetchone()

    finally:
        cursor.close()


def list_of_products(
    search="",
    category="",
    supplier="",
    low_stock_only=False,
    sort="newest"
):
    sql = "SELECT * FROM product WHERE 1=1"
    params = []

    if search:
        sql += """
            AND (
                product_name LIKE %s
                OR category LIKE %s
                OR supplier LIKE %s
                OR CAST(product_id AS CHAR) LIKE %s
            )
        """

        search_value = f"%{search}%"
        params.extend([search_value] * 4)

    if category:
        sql += " AND category = %s"
        params.append(category)

    if supplier:
        sql += " AND supplier = %s"
        params.append(supplier)

    if low_stock_only:
        sql += " AND quantity_in_stock <= reorder_level"

    allowed_sorts = {
        "newest": "date_added DESC",
        "oldest": "date_added ASC",
        "name_asc": "product_name ASC",
        "name_desc": "product_name DESC",
        "price_asc": "unit_price ASC",
        "price_desc": "unit_price DESC",
        "quantity_asc": "quantity_in_stock ASC",
        "quantity_desc": "quantity_in_stock DESC"
    }

    sql += " ORDER BY " + allowed_sorts.get(
        sort,
        allowed_sorts["newest"]
    )

    cursor = mysql.connection.cursor()

    try:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

    finally:
        cursor.close()


def get_product(product_id):
    cursor = mysql.connection.cursor()

    try:
        cursor.execute(
            "SELECT * FROM product WHERE product_id = %s",
            (product_id,)
        )

        return cursor.fetchone()

    finally:
        cursor.close()


def create_product(data):
    cursor = mysql.connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO product (
                product_name,
                category,
                supplier,
                unit_price,
                quantity_in_stock,
                reorder_level
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, data)

        mysql.connection.commit()
        return cursor.lastrowid

    except Exception:
        mysql.connection.rollback()
        raise

    finally:
        cursor.close()


def update_product(product_id, data):
    cursor = mysql.connection.cursor()

    try:
        cursor.execute("""
            UPDATE product
            SET
                product_name = %s,
                category = %s,
                supplier = %s,
                unit_price = %s,
                quantity_in_stock = %s,
                reorder_level = %s
            WHERE product_id = %s
        """, (*data, product_id))

        mysql.connection.commit()
        return cursor.rowcount

    except Exception:
        mysql.connection.rollback()
        raise

    finally:
        cursor.close()


def delete_product_record(product_id):
    cursor = mysql.connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM product WHERE product_id = %s",
            (product_id,)
        )

        mysql.connection.commit()
        return cursor.rowcount

    except Exception:
        mysql.connection.rollback()
        raise

    finally:
        cursor.close()


def filter_options():
    cursor = mysql.connection.cursor()

    try:
        cursor.execute(
            "SELECT DISTINCT category FROM product ORDER BY category"
        )
        categories = [
            row["category"] for row in cursor.fetchall()
        ]

        cursor.execute(
            "SELECT DISTINCT supplier FROM product ORDER BY supplier"
        )
        suppliers = [
            row["supplier"] for row in cursor.fetchall()
        ]

        return categories, suppliers

    finally:
        cursor.close()


# -------------------------
# Authentication and validation
# -------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


def validate_email(email):
    pattern = (r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    return bool(re.fullmatch(pattern, email))


def validate_product_form():
    product_name = request.form.get("product_name", "").strip()
    category = request.form.get("category", "").strip()
    supplier = request.form.get("supplier", "").strip()

    unit_price = request.form.get("unit_price", "").strip()
    quantity = request.form.get("quantity_in_stock", "").strip()
    reorder_level = request.form.get("reorder_level", "").strip()

    if not product_name or not category or not supplier:
        raise ValueError("Please fill in all required product details.")

    try:
        unit_price = float(unit_price)
        quantity = int(quantity)
        reorder_level = int(reorder_level)

    except ValueError:
        raise ValueError(
            "Price, quantity and reorder level must be valid numbers."
        )

    if unit_price < 0 or quantity < 0 or reorder_level < 0:
        raise ValueError(
            "Price, quantity and reorder level cannot be negative."
        )

    return (
        product_name,
        category,
        supplier,
        unit_price,
        quantity,
        reorder_level
    )


# -------------------------
# Flask application
# -------------------------

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    app.config.setdefault("MYSQL_CURSORCLASS", "DictCursor")

    mysql.init_app(app)

    # Home page

    @app.get("/", endpoint="home")
    def home():
        if "user_id" in session:
            return redirect(url_for("dashboard"))

        return render_template("home.html")

    # Registration

    @app.route("/register", methods=["GET", "POST"], endpoint="register")
    def register():

        if "user_id" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not full_name or not email or not password:
                flash("Please complete all required fields.", "error")

            elif not validate_email(email):
                flash("Please enter a valid email address.", "error")

            elif len(password) < 8:
                flash("Password must contain at least 8 characters.", "error")

            elif password != confirm_password:
                flash("Passwords do not match.", "error")

            else:
                try:
                    create_user(full_name, email, password)

                    flash(
                        "Your account has been created. Please log in.",
                        "success"
                    )

                    return redirect(url_for("login"))

                except IntegrityError:
                    flash(
                        "An account with this email already exists.",
                        "error"
                    )

                except Exception:
                    app.logger.exception("Registration failed")
                    flash(
                        "An error occurred while creating your account.",
                        "error"
                    )

        return render_template("authentication/register.html")

    # Login

    @app.route("/login", methods=["GET", "POST"], endpoint="login")
    def login():

        if "user_id" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            user = verify_user(email, password)

            if user:
                session.clear()
                session["user_id"] = user["user_id"]
                session["user_name"] = user["full_name"]
                session["user_email"] = user["email"]
                session.permanent = True

                flash("Welcome back!", "success")
                return redirect(url_for("dashboard"))

            flash("Invalid email or password.", "error")

        return render_template("authentication/login.html")

    # Logout

    @app.post("/logout", endpoint="logout")
    @login_required
    def logout():
        session.clear()
        flash("You have been signed out.", "success")

        return redirect(url_for("login"))

    # Dashboard

    @app.get("/dashboard", endpoint="dashboard")
    @login_required
    def dashboard():

        summary = product_summary()
        products = list_of_products()
        categories, suppliers = filter_options()

        return render_template(
            "dashboard/index.html",
            summary=summary,
            products=products,
            categories=categories,
            suppliers=suppliers,
            search=""
    )
    # Product search and filtering

    @app.get("/products/search", endpoint="search_products")
    @login_required
    def search_products():

        search = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        supplier = request.args.get("supplier", "").strip()

        low_stock_only = (
            request.args.get("low_stock", "").lower()
            in ("true", "1", "yes")
        )

        products = list_of_products(
            search=search,
            category=category,
            supplier=supplier,
            low_stock_only=low_stock_only
        )

        result = []

        for product in products:
            result.append({
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "supplier": product["supplier"],
                "unit_price": float(product["unit_price"]),
                "quantity_in_stock": product["quantity_in_stock"],
                "reorder_level": product["reorder_level"],
                "date_added": (
                    product["date_added"].strftime("%Y-%m-%d")
                    if product["date_added"] else ""
                )
            })

        return jsonify(result)

    # Add product

    @app.post("/products", endpoint="add_product")
    @login_required
    def add_product():

        try:
            data = validate_product_form()
            create_product(data)

            flash("Product added successfully.", "success")

        except ValueError as error:
            flash(str(error), "error")

        except Exception:
            app.logger.exception("Product creation failed")
            flash("Unable to add product.", "error")

        return redirect(url_for("dashboard"))

    # Edit product

    @app.route(
        "/products/<int:product_id>/edit",
        methods=["GET", "POST"],
        endpoint="edit_product"
    )
    @login_required
    def edit_product(product_id):

        product = get_product(product_id)

        if not product:
            flash("Product not found.", "error")
            return redirect(url_for("dashboard"))

        if request.method == "POST":

            try:
                data = validate_product_form()
                update_product(product_id, data)

                flash("Product updated successfully.", "success")
                return redirect(url_for("dashboard"))

            except ValueError as error:
                flash(str(error), "error")

            except Exception:
                app.logger.exception("Product update failed")
                flash("Unable to update product.", "error")

        return render_template(
            "dashboard/index.html",
            product=product
        )

    # Delete product

    @app.post(
        "/products/<int:product_id>/delete",
        endpoint="delete_product"
    )
    @login_required
    def remove_product(product_id):

        try:
            deleted = delete_product_record(product_id)

            if deleted:
                flash("Product deleted successfully.", "success")
            else:
                flash("Product not found.", "error")

        except Exception:
            app.logger.exception("Product deletion failed")
            flash("Unable to delete product.", "error")

        return redirect(url_for("dashboard"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
