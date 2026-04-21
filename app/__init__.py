from flask import Flask
from dotenv import load_dotenv
from app.config import Config
from app.extensions import db, login_manager, bcrypt

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.entities import entities_bp
    from app.routes.records import records_bp
    from app.routes.forms import forms_bp
    from app.routes.org_units import org_units_bp
    from app.routes.admin import admin_bp
    from app.routes.applications import applications_bp
    from app.routes.reports import reports_bp
    from app.routes.participants import participants_bp
    from app.routes.programs import programs_bp
    from app.routes.workflow import workflow_bp
    from app.routes.indicators import indicators_bp
    from app.routes.api.auth import api_auth_bp
    from app.routes.api.entities import api_entities_bp
    from app.routes.api.records import api_records_bp
    from app.routes.api.forms import api_forms_bp
    from app.routes.api.sync import api_sync_bp
    from app.routes.api.org_units import api_org_units_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(entities_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(forms_bp)
    app.register_blueprint(org_units_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(participants_bp)
    app.register_blueprint(programs_bp)
    app.register_blueprint(workflow_bp)
    app.register_blueprint(indicators_bp)
    app.register_blueprint(api_auth_bp)
    app.register_blueprint(api_entities_bp)
    app.register_blueprint(api_records_bp)
    app.register_blueprint(api_forms_bp)
    app.register_blueprint(api_sync_bp)
    app.register_blueprint(api_org_units_bp)

    # Jinja2 globals
    from app.utils.role_access import can_access, is_data_entry_only, is_report_viewer_only
    app.jinja_env.globals['can_access'] = can_access
    app.jinja_env.globals['is_data_entry_only'] = is_data_entry_only
    app.jinja_env.globals['is_report_viewer_only'] = is_report_viewer_only

    return app
