from flask import Blueprint, render_template
from flask_login import login_required, current_user

from models import Student, Admission, FeePayment

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "student":
        return "Access Denied", 403

    # 🔒 FIX: Match student correctly
    student = Student.query.filter_by(email=current_user.email).first()

    if not student:
        return "Student profile not found", 404

    admissions = Admission.query.filter_by(student_id=student.id).all()

    return render_template(
        "student_dashboard.html",
        student=student,
        admissions=admissions
    )


@student_bp.route("/receipt/<int:payment_id>")
@login_required
def view_receipt(payment_id):
    if current_user.role != "student":
        return "Access Denied", 403

    payment = FeePayment.query.get_or_404(payment_id)
    admission = Admission.query.get(payment.admission_id)

    student = Student.query.filter_by(email=current_user.email).first()

    if not student or admission.student_id != student.id:
        return "Access Denied", 403

    return render_template(
        "receipt.html",
        payment=payment,
        admission=admission,
        student=student
    )
