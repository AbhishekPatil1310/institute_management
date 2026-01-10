from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import Student, User, db, generate_student_id

auth_bp = Blueprint('auth', __name__)


# ----------------------------
# ADMISSION
# ----------------------------
@auth_bp.route("/admission", methods=["GET", "POST"])
def admission():
    message = ""

    if request.method == "POST":
        name = request.form.get("name")
        mobile = request.form.get("mobile")
        email = request.form.get("email")

        existing_student = Student.query.filter_by(mobile=mobile).first()
        existing_user = User.query.filter_by(email=email).first()

        if existing_student or existing_user:
            message = "Student already registered."
        else:
            student = Student(
                student_id=generate_student_id(),
                name=name,
                mobile=mobile,
                email=email
            )
            db.session.add(student)

            user = User(
                email=email,
                password_hash=generate_password_hash(mobile),
                role="student"
            )
            db.session.add(user)
            db.session.commit()

            message = "Admission successful. Password is your mobile number."

    return render_template("admission.html", message=message)


# ----------------------------
# LOGIN
# ----------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)

            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            elif user.role == "reception":
                return redirect(url_for("reception.dashboard"))
            else:
                return redirect(url_for("student.dashboard"))

        error = "Invalid email or password"

    return render_template("login.html", error=error)


# ----------------------------
# LOGOUT (NEW)
# ----------------------------
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# ----------------------------
# CHANGE PASSWORD (NEW)
# ----------------------------
@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    message = ""

    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")

        if not check_password_hash(current_user.password_hash, old_password):
            message = "Old password is incorrect"
        else:
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            message = "Password changed successfully"

    return render_template("change_password.html", message=message)
