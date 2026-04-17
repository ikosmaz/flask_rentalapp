from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError

from auth import admin_required, roles_required
from models import Customer, EquipmentInstance, EquipmentModel, Rental, db


rentals_bp = Blueprint("rentals", __name__)
PAYMENT_METHODS = ["Kort", "Kontant", "Vipps", "Giro"]
OVERDUE_PERIOD_DAYS = 10


@rentals_bp.route("/")
@roles_required("admin", "user")
def list_rentals():
    status = request.args.get("status", "all")
    employee_filter = request.args.get("employee", "all")
    allowed_statuses = {"all", "active", "overdue", "completed"}
    if status not in allowed_statuses:
        status = "all"

    query = Rental.query
    if status == "active":
        query = query.filter(Rental.return_date.is_(None))
    elif status == "overdue":
        query = query.filter(Rental.return_date.is_(None)).filter(
            func.datediff(date.today(), Rental.rent_date) > OVERDUE_PERIOD_DAYS
        )
    elif status == "completed":
        query = query.filter(Rental.return_date.isnot(None))

    if employee_filter == "me":
        query = query.filter(Rental.employee_id == current_user.employee_id)

    rentals = query.order_by(Rental.rent_date.desc(), Rental.rental_id.desc()).all()
    overdue_rental_ids = {
        r.rental_id
        for r in rentals
        if r.return_date is None and (date.today() - r.rent_date).days > OVERDUE_PERIOD_DAYS
    }

    return render_template(
        "rentals/list.html",
        rentals=rentals,
        status=status,
        employee_filter=employee_filter,
        overdue_rental_ids=overdue_rental_ids,
    )


@rentals_bp.route("/new", methods=["GET", "POST"])
@roles_required("admin", "user")
def create_rental():
    customers = Customer.query.order_by(Customer.name.asc()).all()
    available_instances = _available_equipment_instances()

    if request.method == "POST":
        try:
            rental = Rental(
                customer_id=int(request.form["customer_id"]),
                model_id=int(request.form["model_id"]),
                instans_nr=int(request.form["instans_nr"]),
                rent_date=date.fromisoformat(request.form["rent_date"]),
                payment_method=request.form["payment_method"],
                employee_id=current_user.employee_id,
                deliver_to_customer=(request.form.get("deliver_to_customer") == "on"),
                delivery_cost=request.form.get("delivery_cost") or 0,
            )

            if rental.payment_method not in PAYMENT_METHODS:
                raise ValueError("Invalid payment method")

            active_exists = (
                Rental.query.filter_by(model_id=rental.model_id, instans_nr=rental.instans_nr)
                .filter(Rental.return_date.is_(None))
                .first()
            )
            if active_exists:
                raise ValueError("Selected equipment instance is already rented out")

            db.session.add(rental)
            db.session.commit()
            flash("Rental registered.", "success")
            return redirect(url_for("rentals.list_rentals"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(f"Unable to register rental: {exc}", "danger")

    return render_template(
        "rentals/form.html",
        customers=customers,
        available_instances=available_instances,
        payment_methods=PAYMENT_METHODS,
    )


@rentals_bp.route("/<int:rental_id>/return", methods=["POST"])
@roles_required("admin", "user")
def register_return(rental_id):
    rental = Rental.query.get_or_404(rental_id)
    if rental.return_date is not None:
        flash("Rental is already returned.", "warning")
        return redirect(url_for("rentals.list_rentals"))

    return_date_raw = request.form.get("return_date")
    try:
        rental.return_date = date.fromisoformat(return_date_raw) if return_date_raw else date.today()
        db.session.commit()
        flash("Delivery/return registered.", "success")
    except ValueError:
        db.session.rollback()
        flash("Invalid return date.", "danger")

    return redirect(url_for("rentals.list_rentals"))


@rentals_bp.route("/<int:rental_id>/delete", methods=["POST"])
@admin_required
def delete_rental(rental_id):
    rental = Rental.query.get_or_404(rental_id)
    try:
        db.session.delete(rental)
        db.session.commit()
        flash("Rental deleted.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Unable to delete rental.", "danger")
    return redirect(url_for("rentals.list_rentals"))


@rentals_bp.route("/api/active-rentals")
@roles_required("admin", "user")
def api_active_rentals():
    rentals = (
        Rental.query.filter(Rental.return_date.is_(None))
        .order_by(Rental.rent_date.desc(), Rental.rental_id.desc())
        .all()
    )
    payload = [
        {
            "rental_id": r.rental_id,
            "customer_id": r.customer_id,
            "model_id": r.model_id,
            "instans_nr": r.instans_nr,
            "rent_date": r.rent_date.isoformat(),
            "employee_id": r.employee_id,
        }
        for r in rentals
    ]
    return jsonify(payload)


@rentals_bp.route("/api/equipment/available")
@roles_required("admin", "user")
def api_available_equipment():
    payload = []
    for instance in _available_equipment_instances():
        payload.append(
            {
                "model_id": instance.model_id,
                "instans_nr": instance.instans_nr,
                "type": instance.model_ref.type,
                "brand": instance.model_ref.brand,
                "model": instance.model_ref.model,
                "daily_price": float(instance.model_ref.daily_price),
            }
        )
    return jsonify(payload)


def _available_equipment_instances():
    active_subquery = (
        db.session.query(Rental.model_id.label("model_id"), Rental.instans_nr.label("instans_nr"))
        .filter(Rental.return_date.is_(None))
        .subquery()
    )

    return (
        db.session.query(EquipmentInstance)
        .join(EquipmentModel, EquipmentModel.model_id == EquipmentInstance.model_id)
        .outerjoin(
            active_subquery,
            and_(
                active_subquery.c.model_id == EquipmentInstance.model_id,
                active_subquery.c.instans_nr == EquipmentInstance.instans_nr,
            ),
        )
        .filter(active_subquery.c.model_id.is_(None))
        .order_by(EquipmentModel.type.asc(), EquipmentInstance.instans_nr.asc())
        .all()
    )
