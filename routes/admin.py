from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash

from auth import admin_required
from models import Employee, EmployeeLogin, db


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users")
@admin_required
def list_users():
    search_query = request.args.get("q", "").strip()
    like = f"%{search_query}%"

    users_query = EmployeeLogin.query.join(Employee, Employee.employee_id == EmployeeLogin.employee_id)
    employees_query = Employee.query.options(joinedload(Employee.login))

    if search_query:
        users_query = users_query.filter(Employee.name.ilike(like))
        employees_query = employees_query.filter(Employee.name.ilike(like))

    users = users_query.order_by(EmployeeLogin.username.asc()).all()
    employees = employees_query.order_by(Employee.name.asc(), Employee.employee_id.asc()).all()
    return render_template(
        "admin/users_list.html",
        users=users,
        employees=employees,
        search_query=search_query,
    )


@admin_bp.route("/employees/new", methods=["GET", "POST"])
@admin_required
def create_employee():
    if request.method == "POST":
        employee_name = request.form.get("employee_name", "").strip()
        employee_phone = request.form.get("employee_phone", "").strip() or None

        if not employee_name:
            flash("Employee name is required.", "danger")
            return render_template("admin/employee_form.html", employee=None)

        try:
            employee = Employee(name=employee_name, phone=employee_phone)
            db.session.add(employee)
            db.session.commit()
            flash("Employee created.", "success")
            return redirect(url_for("admin.list_users"))
        except IntegrityError:
            db.session.rollback()
            flash("Unable to create employee.", "danger")

    return render_template("admin/employee_form.html", employee=None)


@admin_bp.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)

    if request.method == "POST":
        employee_name = request.form.get("employee_name", "").strip()
        employee_phone = request.form.get("employee_phone", "").strip() or None

        if not employee_name:
            flash("Employee name is required.", "danger")
            return render_template("admin/employee_form.html", employee=employee)

        try:
            employee.name = employee_name
            employee.phone = employee_phone
            db.session.commit()
            flash("Employee updated.", "success")
            return redirect(url_for("admin.list_users"))
        except IntegrityError:
            db.session.rollback()
            flash("Unable to update employee.", "danger")

    return render_template("admin/employee_form.html", employee=employee)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def create_user():
    if request.method == "POST":
        employee_id_raw = request.form.get("employee_id", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "user").strip()
        is_active = request.form.get("is_active") == "on"
        form_data = {
            "employee_id": employee_id_raw,
            "username": username,
            "role": role,
            "is_active": is_active,
        }

        if not employee_id_raw or not username or not password:
            flash("Employee, username and password are required.", "danger")
            return render_template(
                "admin/user_form.html",
                user=None,
                available_employees=_employees_without_login(),
                form_data=form_data,
            )

        if role not in {"admin", "user"}:
            flash("Invalid role.", "danger")
            return render_template(
                "admin/user_form.html",
                user=None,
                available_employees=_employees_without_login(),
                form_data=form_data,
            )

        try:
            employee_id = int(employee_id_raw)
        except ValueError:
            flash("Invalid employee selection.", "danger")
            return render_template(
                "admin/user_form.html",
                user=None,
                available_employees=_employees_without_login(),
                form_data=form_data,
            )

        employee = Employee.query.filter_by(employee_id=employee_id).first()
        if employee is None:
            flash("Selected employee does not exist.", "danger")
            return render_template(
                "admin/user_form.html",
                user=None,
                available_employees=_employees_without_login(),
                form_data=form_data,
            )

        existing_login = EmployeeLogin.query.filter_by(employee_id=employee_id).first()
        if existing_login:
            flash("Selected employee already has a user account.", "danger")
            return render_template(
                "admin/user_form.html",
                user=None,
                available_employees=_employees_without_login(),
                form_data=form_data,
            )

        try:
            login = EmployeeLogin(
                employee_id=employee.employee_id,
                username=username,
                password_hash=generate_password_hash(password),
                role=role,
                is_active=is_active,
            )
            db.session.add(login)
            db.session.commit()
            flash("User created.", "success")
            return redirect(url_for("admin.list_users"))
        except IntegrityError:
            db.session.rollback()
            flash("Unable to create user (username may already exist).", "danger")
            return render_template(
                "admin/user_form.html",
                user=None,
                available_employees=_employees_without_login(),
                form_data=form_data,
            )

    available_employees = _employees_without_login()
    selected_employee_id = request.args.get("employee_id", "").strip()
    if selected_employee_id not in {str(emp.employee_id) for emp in available_employees}:
        selected_employee_id = ""

    return render_template(
        "admin/user_form.html",
        user=None,
        available_employees=available_employees,
        form_data={
            "employee_id": selected_employee_id,
            "username": "",
            "role": "user",
            "is_active": True,
        },
    )


@admin_bp.route("/users/<int:employee_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(employee_id):
    user = EmployeeLogin.query.get_or_404(employee_id)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "user").strip()
        is_active = request.form.get("is_active") == "on"

        if not username:
            flash("Username is required.", "danger")
            return render_template("admin/user_form.html", user=user)

        if role not in {"admin", "user"}:
            flash("Invalid role.", "danger")
            return render_template("admin/user_form.html", user=user)

        try:
            user.username = username
            user.role = role
            user.is_active = is_active
            if password:
                user.password_hash = generate_password_hash(password)

            if user.employee_id == current_user.employee_id and not user.is_active:
                flash("You cannot deactivate your own account.", "danger")
                db.session.rollback()
                return render_template("admin/user_form.html", user=user)

            db.session.commit()
            flash("User updated.", "success")
            return redirect(url_for("admin.list_users"))
        except IntegrityError:
            db.session.rollback()
            flash("Unable to update user (username may already exist).", "danger")

    return render_template("admin/user_form.html", user=user)


@admin_bp.route("/users/<int:employee_id>/delete", methods=["POST"])
@admin_required
def delete_user(employee_id):
    user = EmployeeLogin.query.get_or_404(employee_id)

    if user.employee_id == current_user.employee_id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.list_users"))

    try:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Unable to delete user.", "danger")

    return redirect(url_for("admin.list_users"))


def _employees_without_login():
    return (
        Employee.query.outerjoin(EmployeeLogin, Employee.employee_id == EmployeeLogin.employee_id)
        .filter(EmployeeLogin.employee_id.is_(None))
        .order_by(Employee.name.asc(), Employee.employee_id.asc())
        .all()
    )
