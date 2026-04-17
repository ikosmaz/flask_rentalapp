from datetime import date, timedelta

from flask import Blueprint, render_template, request
from flask_login import current_user
from sqlalchemy import desc, func

from auth import roles_required
from models import Customer, EquipmentModel, Rental, db


stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/")
@roles_required("admin", "user")
def stats_home():
    today = date.today()
    default_date_to = today
    default_date_from = today - timedelta(days=30)

    date_to = _parse_date(request.args.get("date_to")) or default_date_to
    date_from = _parse_date(request.args.get("date_from")) or default_date_from

    customer_list = Customer.query.order_by(Customer.name.asc()).all()

    active_rentals_me = (
        Rental.query.filter(Rental.return_date.is_(None), Rental.employee_id == current_user.employee_id)
        .order_by(Rental.rent_date.desc())
        .all()
    )
    active_rentals_all = (
        Rental.query.filter(Rental.return_date.is_(None))
        .order_by(Rental.rent_date.desc(), Rental.rental_id.desc())
        .all()
    )
    customer_count = len(customer_list)
    active_rentals_me_count = len(active_rentals_me)
    active_rentals_all_count = len(active_rentals_all)

    completed_count = (
        Rental.query.filter(Rental.return_date.isnot(None))
        .filter(Rental.return_date.between(date_from, date_to))
        .count()
    )

    rental_days = func.datediff(func.coalesce(Rental.return_date, func.curdate()), Rental.rent_date) + 1
    income_rows = (
        db.session.query(
            Rental.model_id,
            EquipmentModel.type,
            EquipmentModel.brand,
            EquipmentModel.model,
            func.sum((rental_days * EquipmentModel.daily_price) + Rental.delivery_cost).label("income"),
        )
        .join(EquipmentModel, EquipmentModel.model_id == Rental.model_id)
        .group_by(Rental.model_id, EquipmentModel.type, EquipmentModel.brand, EquipmentModel.model)
        .order_by(desc("income"))
        .all()
    )
    income_chart_labels = [f"{row.type} {row.brand} {row.model}" for row in income_rows]
    income_chart_values = [float(row.income or 0) for row in income_rows]

    top_rented_equipment = (
        db.session.query(
            EquipmentModel.model_id,
            EquipmentModel.type,
            EquipmentModel.brand,
            EquipmentModel.model,
            func.count(Rental.rental_id).label("rentals"),
        )
        .join(Rental, Rental.model_id == EquipmentModel.model_id)
        .group_by(
            EquipmentModel.model_id,
            EquipmentModel.type,
            EquipmentModel.brand,
            EquipmentModel.model,
        )
        .having(func.count(Rental.rental_id) > 0)
        .order_by(desc("rentals"))
        .limit(3)
        .all()
    )

    return render_template(
        "stats/index.html",
        customer_list=customer_list,
        customer_count=customer_count,
        active_rentals_me=active_rentals_me,
        active_rentals_me_count=active_rentals_me_count,
        active_rentals_all=active_rentals_all,
        active_rentals_all_count=active_rentals_all_count,
        completed_count=completed_count,
        income_rows=income_rows,
        income_chart_labels=income_chart_labels,
        income_chart_values=income_chart_values,
        top_rented_equipment=top_rented_equipment,
        date_from=date_from,
        date_to=date_to,
    )


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
