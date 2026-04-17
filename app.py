from datetime import date, datetime

from flask import Flask

from auth import auth_bp, login_manager
from config import Config
from models import db
from routes.admin import admin_bp
from routes.customers import customers_bp
from routes.dashboard import dashboard_bp
from routes.equipment import equipment_bp
from routes.rentals import rentals_bp
from routes.stats import stats_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.template_filter("date_dmy")
    def date_dmy(value):
        if value is None:
            return ""
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            return value.strftime("%d-%m-%Y")
        return value

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(equipment_bp, url_prefix="/equipment")
    app.register_blueprint(rentals_bp, url_prefix="/rentals")
    app.register_blueprint(stats_bp, url_prefix="/stats")

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True)
