from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class City(db.Model):
    __tablename__ = "city"

    postnr = db.Column(db.String(4), primary_key=True)
    city = db.Column(db.String(100), nullable=False)


class Address(db.Model):
    __tablename__ = "address"

    address_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    street = db.Column(db.String(100), nullable=False)
    gatenr = db.Column(db.String(4), nullable=False)
    city_postnr = db.Column(db.String(4), db.ForeignKey("city.postnr"), nullable=False)

    city_ref = db.relationship("City")


class Customer(db.Model):
    __tablename__ = "customer"

    customer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255))
    invoice_address_id = db.Column(
        db.Integer, db.ForeignKey("address.address_id"), nullable=False
    )
    delivery_address_id = db.Column(
        db.Integer, db.ForeignKey("address.address_id"), nullable=False
    )

    invoice_address = db.relationship("Address", foreign_keys=[invoice_address_id])
    delivery_address = db.relationship("Address", foreign_keys=[delivery_address_id])


class CustomerPhone(db.Model):
    __tablename__ = "customer_phone"

    phone = db.Column(db.String(20), primary_key=True)
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.customer_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )


class Employee(db.Model):
    __tablename__ = "employee"

    employee_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))


class EmployeeLogin(UserMixin, db.Model):
    __tablename__ = "employee_login"

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employee.employee_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    employee = db.relationship("Employee", backref=db.backref("login", uselist=False))

    def get_id(self):
        return str(self.employee_id)

    @property
    def is_admin(self):
        return self.role == "admin"


class EquipmentCategory(db.Model):
    __tablename__ = "equipment_category"

    category_id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)


class EquipmentModel(db.Model):
    __tablename__ = "equipment_model"

    model_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    daily_price = db.Column(db.Numeric(6, 2), nullable=False)
    total_quantity = db.Column(db.Integer, nullable=False)
    quantity_in_stock = db.Column(db.Integer, nullable=False, default=0)
    equipment_category_id = db.Column(
        db.Integer, db.ForeignKey("equipment_category.category_id"), nullable=False
    )

    category_ref = db.relationship("EquipmentCategory")


class EquipmentInstance(db.Model):
    __tablename__ = "equipment_instance"

    model_id = db.Column(
        db.Integer,
        db.ForeignKey("equipment_model.model_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    instans_nr = db.Column(db.Integer, primary_key=True)
    last_maintenance = db.Column(db.Date)
    next_maintenance = db.Column(db.Date)

    model_ref = db.relationship("EquipmentModel")


class Rental(db.Model):
    __tablename__ = "rental"

    rental_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.customer_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    model_id = db.Column(db.Integer, nullable=False)
    instans_nr = db.Column(db.Integer, nullable=False)
    rent_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date)
    payment_method = db.Column(db.String(20), nullable=False)
    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employee.employee_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    deliver_to_customer = db.Column(db.Boolean, nullable=False, default=False)
    delivery_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint(
            "customer_id", "model_id", "instans_nr", "rent_date", name="uk_rental_natural"
        ),
        db.ForeignKeyConstraint(
            ["model_id", "instans_nr"],
            ["equipment_instance.model_id", "equipment_instance.instans_nr"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="fk_rental_instance",
        ),
    )

    customer = db.relationship("Customer")
    employee = db.relationship("Employee")
    equipment_instance = db.relationship(
        "EquipmentInstance",
        primaryjoin=(
            "and_(Rental.model_id == EquipmentInstance.model_id, "
            "Rental.instans_nr == EquipmentInstance.instans_nr)"
        ),
        foreign_keys=[model_id, instans_nr],
        viewonly=True,
    )
