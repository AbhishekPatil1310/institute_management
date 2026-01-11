from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from datetime import date

from models import (
    db,
    Student,
    Batch,
    Admission,
    FeePayment,
    BatchPaymentSource,
    PaymentSource,
)

reception_bp = Blueprint("reception", __name__, url_prefix="/reception")


# -------------------------------------------------
# RECEPTION DASHBOARD
# -------------------------------------------------
@reception_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if current_user.role != "reception":
        return "Access Denied", 403

    student = None
    admissions = []
    batches = Batch.query.filter_by(status="Active").all()
    message = ""
    error = ""

    new_admission_sources = []
    existing_batch_sources = {}

    if request.method == "POST":
        action = request.form.get("action")
        student_id = request.form.get("student_id")

        # Always reload student if available
        if student_id:
            student = Student.query.get(int(student_id))
            if student:
                admissions = Admission.query.filter_by(
                    student_id=student.id
                ).all()

        # --------------------
        # SEARCH STUDENT
        # --------------------
        if action == "search":
            mobile = request.form.get("mobile")
            student = Student.query.filter_by(mobile=mobile).first()

            if not student:
                error = "No student record found. Ask student to fill admission form."
            else:
                admissions = Admission.query.filter_by(
                    student_id=student.id
                ).all()

        # --------------------
        # NEW ADMISSION
        # --------------------
        elif action == "new_admission":
            batch_id = int(request.form.get("batch_id"))
            paid_amount = int(request.form.get("paid_amount"))
            received_in = request.form.get("received_in")
            remarks = request.form.get("remarks")

            if not received_in:
                error = "Payment method is required."
            else:
                received_in = int(received_in)  # ✅ FIX: normalize type

                batch = Batch.query.get(batch_id)

                existing_adm = Admission.query.filter_by(
                    student_id=student.id,
                    batch_id=batch.id,
                ).first()

                if existing_adm:
                    error = "Student is already admitted to this batch."
                else:
                    admission = Admission(
                        student_id=student.id,
                        batch_id=batch.id,
                        total_fee=batch.total_fee,
                        paid_amount=paid_amount,
                        pending_amount=batch.total_fee - paid_amount,
                        remarks=remarks,
                        admission_date=date.today(),
                        status="Completed"
                        if paid_amount >= batch.total_fee
                        else "Active",
                    )
                    db.session.add(admission)
                    db.session.commit()

                    payment = FeePayment(
                        admission_id=admission.id,
                        amount=paid_amount,
                        received_in=received_in,
                    )
                    db.session.add(payment)
                    db.session.commit()

                    message = "Admission completed successfully."

            admissions = Admission.query.filter_by(
                student_id=student.id
            ).all()

        # --------------------
        # PAY PENDING FEE
        # --------------------
        elif action == "pay_pending":
            admission_id = int(request.form.get("admission_id"))
            paid_amount = int(request.form.get("paid_amount"))
            received_in = request.form.get("received_in")

            if not received_in:
                error = "Payment method is required."
            else:
                received_in = int(received_in)  # ✅ already correct, kept consistent

                admission = Admission.query.get(admission_id)

                if paid_amount > admission.pending_amount:
                    error = f"Amount exceeds pending fee (₹{admission.pending_amount})"
                else:
                    payment = FeePayment(
                        admission_id=admission.id,
                        amount=paid_amount,
                        received_in=received_in,
                    )
                    db.session.add(payment)

                    admission.paid_amount += paid_amount
                    admission.pending_amount -= paid_amount

                    if admission.pending_amount == 0:
                        admission.status = "Completed"

                    db.session.commit()
                    message = "Payment recorded successfully."

            admissions = Admission.query.filter_by(
                student_id=student.id
            ).all()

    # -------------------------------------------------
    # LOAD PAYMENT SOURCES
    # -------------------------------------------------

    selected_batch_id = request.form.get("batch_id")
    if selected_batch_id:
        new_admission_sources = (
            BatchPaymentSource.query
            .filter_by(batch_id=int(selected_batch_id))
            .order_by(BatchPaymentSource.priority)
            .all()
        )

    if student:
        for adm in admissions:
            sources = (
                BatchPaymentSource.query
                .filter_by(batch_id=adm.batch_id)
                .order_by(BatchPaymentSource.priority)
                .all()
            )
            existing_batch_sources[adm.batch_id] = sources

    # ✅ CLEAN, SAFE LOOKUP MAP
    payment_source_map = {
        ps.id: ps
        for ps in PaymentSource.query.all()
    }

    return render_template(
        "reception_dashboard.html",
        student=student,
        admissions=admissions,
        batches=batches,
        payment_sources=new_admission_sources,
        existing_batch_sources=existing_batch_sources,
        payment_source_map=payment_source_map,
        message=message,
        error=error,
    )


# -------------------------------------------------
# RECEIPT VIEW (RECEPTION)
# -------------------------------------------------
@reception_bp.route("/receipt/<int:payment_id>")
@login_required
def view_receipt(payment_id):
    if current_user.role not in ["reception", "admin"]:
        return "Access Denied", 403

    payment = FeePayment.query.get_or_404(payment_id)
    admission = Admission.query.get_or_404(payment.admission_id)
    student = Student.query.get_or_404(admission.student_id)

    return render_template(
        "receipt.html",
        payment=payment,
        admission=admission,
        student=student,
    )
