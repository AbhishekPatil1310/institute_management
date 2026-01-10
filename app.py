import os
from flask import Flask
from flask_login import LoginManager
from models import db
from dotenv import load_dotenv

load_dotenv()


login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)

    # ----------------------
    # CONFIG (AIVEN MYSQL)
    # ----------------------
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "fallback-secret-key"
    )

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")

    # Aiven MySQL needs this fix sometimes
    if database_url.startswith("mysql://"):
        database_url = database_url.replace(
            "mysql://", "mysql+pymysql://", 1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ----------------------
    # INIT EXTENSIONS
    # ----------------------
    db.init_app(app)
    login_manager.init_app(app)

    # ----------------------
    # USER LOADER
    # ----------------------
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ----------------------
    # BLUEPRINTS
    # ----------------------
    from auth.auth_routes import auth_bp
    from admin.admin_routes import admin_bp
    from reception.reception_routes import reception_bp
    from student.student_routes import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reception_bp)
    app.register_blueprint(student_bp)

    return app


# REQUIRED BY VERCEL
app = create_app()


if __name__ == "__main__":
    # Use environment port for deployment (Render/Railway/Heroku)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)