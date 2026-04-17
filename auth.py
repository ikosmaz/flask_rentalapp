from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from models import EmployeeLogin


auth_bp = Blueprint("auth", __name__)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    if not user_id:
        return None
    return EmployeeLogin.query.get(int(user_id))


def roles_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in allowed_roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("dashboard.home"))
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def admin_required(view_func):
    return roles_required("admin")(view_func)


def _verify_password(stored_password_hash, provided_password):
    # Dev fallback: allow plain-text seed passwords if hashes are not set yet.
    if stored_password_hash.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored_password_hash, provided_password)
    return stored_password_hash == provided_password


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = EmployeeLogin.query.filter_by(username=username).first()
        if not user or not user.is_active:
            flash("Invalid username or inactive account.", "danger")
            return render_template("login.html")

        if not _verify_password(user.password_hash, password):
            flash("Invalid username/password.", "danger")
            return render_template("login.html")

        login_user(user)
        flash("Logged in successfully.", "success")

        next_url = request.args.get("next")
        return redirect(next_url or url_for("dashboard.home"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You are now logged out.", "info")
    return redirect(url_for("auth.login"))
