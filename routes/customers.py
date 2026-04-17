from collections import defaultdict

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from auth import roles_required
from models import Address, City, Customer, CustomerPhone, db


customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/")
@roles_required("admin", "user")
def list_customers():
    search = request.args.get("q", "").strip()
    query = Customer.query
    if search:
        like = f"%{search}%"
        query = query.filter((Customer.name.ilike(like)) | (Customer.email.ilike(like)))

    customers = query.order_by(Customer.name.asc()).all()
    customer_ids = [c.customer_id for c in customers]
    phones_by_customer = defaultdict(list)
    if customer_ids:
        phone_rows = (
            CustomerPhone.query.filter(CustomerPhone.customer_id.in_(customer_ids))
            .order_by(CustomerPhone.customer_id.asc(), CustomerPhone.phone.asc())
            .all()
        )
        for row in phone_rows:
            phones_by_customer[row.customer_id].append(row.phone)

    phone_display = {
        customer_id: ", ".join(phone_list) for customer_id, phone_list in phones_by_customer.items()
    }

    return render_template(
        "customers/list.html",
        customers=customers,
        search=search,
        phone_display=phone_display,
    )


@customers_bp.route("/new", methods=["GET", "POST"])
@roles_required("admin", "user")
def create_customer():
    if request.method == "POST":
        try:
            invoice_postnr = request.form["invoice_postnr"].strip()
            invoice_city = request.form.get("invoice_city", "").strip()
            delivery_postnr = request.form["delivery_postnr"].strip()
            delivery_city = request.form.get("delivery_city", "").strip()
            if invoice_postnr == delivery_postnr:
                shared_city = invoice_city or delivery_city
                invoice_city = invoice_city or shared_city
                delivery_city = delivery_city or shared_city

            _ensure_city_exists(invoice_postnr, invoice_city)
            _ensure_city_exists(delivery_postnr, delivery_city)

            invoice_address = Address(
                street=request.form["invoice_street"].strip(),
                gatenr=request.form["invoice_gatenr"].strip(),
                city_postnr=invoice_postnr,
            )
            delivery_address = Address(
                street=request.form["delivery_street"].strip(),
                gatenr=request.form["delivery_gatenr"].strip(),
                city_postnr=delivery_postnr,
            )
            db.session.add(invoice_address)
            db.session.add(delivery_address)
            db.session.flush()

            customer = Customer(
                customer_id=int(request.form["customer_id"]),
                name=request.form["name"].strip(),
                type=request.form["type"],
                email=request.form.get("email", "").strip() or None,
                invoice_address_id=invoice_address.address_id,
                delivery_address_id=delivery_address.address_id,
            )
            db.session.add(customer)

            phones = _extract_phones(request.form.get("phones", ""))
            for phone in phones:
                db.session.add(CustomerPhone(phone=phone, customer_id=customer.customer_id))

            db.session.commit()
            flash("Customer created.", "success")
            return redirect(url_for("customers.list_customers"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(f"Unable to create customer: {exc}", "danger")

    return render_template("customers/form.html", customer=None)


@customers_bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@roles_required("admin", "user")
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    if request.method == "POST":
        try:
            invoice_postnr = request.form["invoice_postnr"].strip()
            invoice_city = request.form.get("invoice_city", "").strip()
            delivery_postnr = request.form["delivery_postnr"].strip()
            delivery_city = request.form.get("delivery_city", "").strip()
            if invoice_postnr == delivery_postnr:
                shared_city = invoice_city or delivery_city
                invoice_city = invoice_city or shared_city
                delivery_city = delivery_city or shared_city

            _ensure_city_exists(invoice_postnr, invoice_city)
            _ensure_city_exists(delivery_postnr, delivery_city)

            customer.name = request.form["name"].strip()
            customer.type = request.form["type"]
            customer.email = request.form.get("email", "").strip() or None

            customer.invoice_address.street = request.form["invoice_street"].strip()
            customer.invoice_address.gatenr = request.form["invoice_gatenr"].strip()
            customer.invoice_address.city_postnr = invoice_postnr

            customer.delivery_address.street = request.form["delivery_street"].strip()
            customer.delivery_address.gatenr = request.form["delivery_gatenr"].strip()
            customer.delivery_address.city_postnr = delivery_postnr

            CustomerPhone.query.filter_by(customer_id=customer.customer_id).delete()
            phones = _extract_phones(request.form.get("phones", ""))
            for phone in phones:
                db.session.add(CustomerPhone(phone=phone, customer_id=customer.customer_id))

            db.session.commit()
            flash("Customer updated.", "success")
            return redirect(url_for("customers.list_customers"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(f"Unable to update customer: {exc}", "danger")

    phone_rows = CustomerPhone.query.filter_by(customer_id=customer.customer_id).all()
    phones = ", ".join(sorted([p.phone for p in phone_rows]))
    return render_template("customers/form.html", customer=customer, phones=phones)


@customers_bp.route("/<int:customer_id>/delete", methods=["POST"])
@roles_required("admin", "user")
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash("Customer deleted.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Customer cannot be deleted due to related data.", "danger")
    return redirect(url_for("customers.list_customers"))


def _extract_phones(raw_value):
    return [part.strip() for part in raw_value.split(",") if part.strip()]


def _ensure_city_exists(postnr, city_name):
    city = City.query.get(postnr)
    if city:
        if city_name and city.city.lower() != city_name.lower():
            raise ValueError(
                f"Postnr {postnr} already exists with city '{city.city}'. "
                f"Use that city name or another postnr."
            )
        return city

    if not city_name:
        raise ValueError(
            f"Postnr {postnr} does not exist. Enter city name to create it."
        )

    city = City(postnr=postnr, city=city_name)
    db.session.add(city)
    db.session.flush()
    return city
