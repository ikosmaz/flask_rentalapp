from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from auth import admin_required, roles_required
from models import EquipmentCategory, EquipmentInstance, EquipmentModel, db


equipment_bp = Blueprint("equipment", __name__)


@equipment_bp.route("/")
@roles_required("admin", "user")
def list_equipment():
    type_filter = request.args.get("type", "").strip()
    category_filter = request.args.get("category", "").strip()
    search = request.args.get("q", "").strip()

    query = EquipmentModel.query
    if type_filter:
        query = query.filter(EquipmentModel.type == type_filter)
    if category_filter:
        query = query.join(EquipmentCategory).filter(EquipmentCategory.category == category_filter)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (EquipmentModel.type.ilike(like))
            | (EquipmentModel.brand.ilike(like))
            | (EquipmentModel.model.ilike(like))
        )

    equipment = query.order_by(EquipmentModel.type.asc(), EquipmentModel.brand.asc()).all()
    equipment_total_quantity = sum(e.total_quantity for e in equipment)
    equipment_total_in_stock = sum(e.quantity_in_stock for e in equipment)
    instance_query = db.session.query(EquipmentInstance).join(EquipmentModel)
    if type_filter:
        instance_query = instance_query.filter(EquipmentModel.type == type_filter)
    if category_filter:
        instance_query = instance_query.join(EquipmentCategory).filter(
            EquipmentCategory.category == category_filter
        )
    if search:
        like = f"%{search}%"
        instance_query = instance_query.filter(
            (EquipmentModel.type.ilike(like))
            | (EquipmentModel.brand.ilike(like))
            | (EquipmentModel.model.ilike(like))
        )
    instances = instance_query.order_by(
        EquipmentModel.type.asc(),
        EquipmentModel.brand.asc(),
        EquipmentInstance.model_id.asc(),
        EquipmentInstance.instans_nr.asc(),
    ).all()

    categories = EquipmentCategory.query.order_by(EquipmentCategory.category.asc()).all()
    distinct_types = [
        row[0]
        for row in db.session.query(EquipmentModel.type)
        .distinct()
        .order_by(EquipmentModel.type.asc())
        .all()
    ]

    return render_template(
        "equipment/list.html",
        equipment=equipment,
        equipment_total_quantity=equipment_total_quantity,
        equipment_total_in_stock=equipment_total_in_stock,
        instances=instances,
        categories=categories,
        distinct_types=distinct_types,
        type_filter=type_filter,
        category_filter=category_filter,
        search=search,
        is_admin=(current_user.role == "admin"),
    )


@equipment_bp.route("/new", methods=["GET", "POST"])
@admin_required
def create_equipment():
    categories = EquipmentCategory.query.order_by(EquipmentCategory.category.asc()).all()
    if request.method == "POST":
        try:
            record = EquipmentModel(
                model_id=int(request.form["model_id"]),
                type=request.form["type"].strip(),
                brand=request.form["brand"].strip(),
                model=request.form["model"].strip(),
                description=request.form.get("description", "").strip() or None,
                daily_price=request.form["daily_price"],
                total_quantity=int(request.form["total_quantity"]),
                quantity_in_stock=int(request.form["quantity_in_stock"]),
                equipment_category_id=int(request.form["equipment_category_id"]),
            )
            db.session.add(record)
            db.session.commit()
            flash("Equipment created.", "success")
            return redirect(url_for("equipment.list_equipment"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(f"Unable to create equipment: {exc}", "danger")

    return render_template("equipment/form.html", record=None, categories=categories)


@equipment_bp.route("/<int:model_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_equipment(model_id):
    record = EquipmentModel.query.get_or_404(model_id)
    categories = EquipmentCategory.query.order_by(EquipmentCategory.category.asc()).all()

    if request.method == "POST":
        try:
            record.type = request.form["type"].strip()
            record.brand = request.form["brand"].strip()
            record.model = request.form["model"].strip()
            record.description = request.form.get("description", "").strip() or None
            record.daily_price = request.form["daily_price"]
            record.total_quantity = int(request.form["total_quantity"])
            record.quantity_in_stock = int(request.form["quantity_in_stock"])
            record.equipment_category_id = int(request.form["equipment_category_id"])
            db.session.commit()
            flash("Equipment updated.", "success")
            return redirect(url_for("equipment.list_equipment"))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(f"Unable to update equipment: {exc}", "danger")

    return render_template("equipment/form.html", record=record, categories=categories)


@equipment_bp.route("/<int:model_id>/delete", methods=["POST"])
@admin_required
def delete_equipment(model_id):
    record = EquipmentModel.query.get_or_404(model_id)
    try:
        db.session.delete(record)
        db.session.commit()
        flash("Equipment deleted.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Equipment cannot be deleted due to related records.", "danger")

    return redirect(url_for("equipment.list_equipment"))


@equipment_bp.route("/instances/new", methods=["GET", "POST"])
@roles_required("admin", "user")
def create_instance():
    models = EquipmentModel.query.order_by(EquipmentModel.type.asc(), EquipmentModel.model_id.asc()).all()
    max_rows = (
        db.session.query(EquipmentInstance.model_id, func.max(EquipmentInstance.instans_nr))
        .group_by(EquipmentInstance.model_id)
        .all()
    )
    max_by_model = {model_id: max_instans for model_id, max_instans in max_rows}
    next_instance_map = {
        str(m.model_id): int((max_by_model.get(m.model_id) or 0) + 1) for m in models
    }

    selected_model_id = request.form.get("model_id", "").strip()
    if not selected_model_id and models:
        selected_model_id = str(models[0].model_id)
    instans_nr_value = request.form.get("instans_nr", "").strip()
    if not instans_nr_value and selected_model_id in next_instance_map:
        instans_nr_value = str(next_instance_map[selected_model_id])

    if request.method == "POST":
        model_id_raw = request.form.get("model_id", "").strip()
        instans_nr_raw = request.form.get("instans_nr", "").strip()
        last_maintenance_raw = request.form.get("last_maintenance", "").strip()
        next_maintenance_raw = request.form.get("next_maintenance", "").strip()

        if not model_id_raw:
            flash("Model ID is required.", "danger")
            return render_template(
                "equipment/instance_new_form.html",
                models=models,
                selected_model_id=selected_model_id,
                instans_nr_value=instans_nr_value,
                next_instance_map=next_instance_map,
            )

        try:
            model_id = int(model_id_raw)
        except ValueError:
            flash("Model ID must be numeric.", "danger")
            return render_template(
                "equipment/instance_new_form.html",
                models=models,
                selected_model_id=selected_model_id,
                instans_nr_value=instans_nr_value,
                next_instance_map=next_instance_map,
            )

        model = EquipmentModel.query.get(model_id)
        if not model:
            flash("Selected model does not exist.", "danger")
            return render_template(
                "equipment/instance_new_form.html",
                models=models,
                selected_model_id=selected_model_id,
                instans_nr_value=instans_nr_value,
                next_instance_map=next_instance_map,
            )

        if not instans_nr_raw:
            instans_nr_raw = str(next_instance_map.get(str(model_id), 1))

        try:
            instans_nr = int(instans_nr_raw)
        except ValueError:
            flash("Instance number must be numeric.", "danger")
            return render_template(
                "equipment/instance_new_form.html",
                models=models,
                selected_model_id=selected_model_id,
                instans_nr_value=instans_nr_raw,
                next_instance_map=next_instance_map,
            )

        existing_count = EquipmentInstance.query.filter_by(model_id=model_id).count()
        if existing_count >= model.total_quantity:
            flash(
                "Cannot add more instances than total quantity for this model. "
                "Increase total quantity first if needed.",
                "danger",
            )
            return render_template(
                "equipment/instance_new_form.html",
                models=models,
                selected_model_id=selected_model_id,
                instans_nr_value=instans_nr_raw,
                next_instance_map=next_instance_map,
            )

        if (
            EquipmentInstance.query.filter_by(model_id=model_id, instans_nr=instans_nr).first()
            is not None
        ):
            flash("This instance number already exists for the selected model.", "danger")
            return render_template(
                "equipment/instance_new_form.html",
                models=models,
                selected_model_id=selected_model_id,
                instans_nr_value=instans_nr_raw,
                next_instance_map=next_instance_map,
            )

        try:
            instance = EquipmentInstance(
                model_id=model_id,
                instans_nr=instans_nr,
                last_maintenance=_parse_optional_date(last_maintenance_raw),
                next_maintenance=_parse_optional_date(next_maintenance_raw),
            )
            db.session.add(instance)
            db.session.commit()
            flash("Equipment instance created.", "success")
            return redirect(url_for("equipment.list_equipment"))
        except ValueError as exc:
            db.session.rollback()
            flash(f"Invalid date value: {exc}", "danger")
        except IntegrityError:
            db.session.rollback()
            flash("Unable to create equipment instance.", "danger")

    return render_template(
        "equipment/instance_new_form.html",
        models=models,
        selected_model_id=selected_model_id,
        instans_nr_value=instans_nr_value,
        next_instance_map=next_instance_map,
    )


@equipment_bp.route("/instances/<int:model_id>/<int:instans_nr>/edit", methods=["GET", "POST"])
@roles_required("admin", "user")
def edit_instance(model_id, instans_nr):
    instance = EquipmentInstance.query.filter_by(model_id=model_id, instans_nr=instans_nr).first_or_404()

    if request.method == "POST":
        try:
            instance.last_maintenance = _parse_optional_date(
                request.form.get("last_maintenance", "").strip()
            )
            instance.next_maintenance = _parse_optional_date(
                request.form.get("next_maintenance", "").strip()
            )
            db.session.commit()
            flash("Equipment instance updated.", "success")
            return redirect(url_for("equipment.list_equipment"))
        except ValueError as exc:
            db.session.rollback()
            flash(f"Invalid date value: {exc}", "danger")
        except IntegrityError:
            db.session.rollback()
            flash("Unable to update equipment instance.", "danger")

    return render_template("equipment/instance_form.html", instance=instance)


def _parse_optional_date(value):
    if not value:
        return None
    return date.fromisoformat(value)
