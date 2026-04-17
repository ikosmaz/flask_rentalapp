from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from models import EquipmentModel, Rental, db


dashboard_bp = Blueprint("dashboard", __name__)
RENTAL_DUE_PERIOD_DAYS = 7

@dashboard_bp.route("/")
@login_required
def home():
    active_rentals = db_count_active_rentals()
    available_equipment = db_total_available_equipment()
    latest_rentals = (
        Rental.query.order_by(Rental.rent_date.desc(), Rental.rental_id.desc()).limit(5).all()
    )

    overdue_rentals = (
        Rental.query.filter(Rental.return_date.is_(None))
        .filter(func.datediff(date.today(), Rental.rent_date) > RENTAL_DUE_PERIOD_DAYS)
        .order_by(Rental.rent_date.asc())
        .all()
    )
    overdue_count = len(overdue_rentals)
    completed_rentals = Rental.query.filter(Rental.return_date.isnot(None)).count()

    chart_data = {
        "labels": ["Active", "Completed", "Overdue"],
        "values": [
            active_rentals,
            completed_rentals,
            overdue_count,
        ],
    }

    return render_template(
        "dashboard.html",
        active_rentals=active_rentals,
        available_equipment=available_equipment,
        latest_rentals=latest_rentals,
        chart_data=chart_data,
        overdue_rentals=overdue_rentals,
        overdue_count=overdue_count,
        due_period_days=RENTAL_DUE_PERIOD_DAYS,
    )


def db_count_active_rentals():
    return Rental.query.filter(Rental.return_date.is_(None)).count()


def db_total_available_equipment():
    value = db.session.query(func.coalesce(func.sum(EquipmentModel.quantity_in_stock), 0)).scalar()
    return int(value or 0)
