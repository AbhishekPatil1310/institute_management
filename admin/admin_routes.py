from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, date

from models import (
    db,
    Batch,
    Admission,
    FeePayment,
    PaymentSource,
    BatchPaymentSource,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# -------------------------------------------------
# ADMIN DASHBOARD
# -------------------------------------------------
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "admin":
        return "Access Denied", 403

    total_collection = db.session.query(
        func.sum(FeePayment.amount)
    ).scalar() or 0

    total_pending = db.session.query(
        func.sum(Admission.pending_amount)
    ).scalar() or 0

    batch_stats = (
        db.session.query(
            Batch.batch_code,
            Batch.course_name,
            func.count(Admission.id).label("student_count"),
            func.sum(Admission.paid_amount).label("paid_total"),
            func.sum(Admission.pending_amount).label("pending_total"),
        )
        .outerjoin(Admission, Admission.batch_id == Batch.id)
        .group_by(Batch.id)
        .all()
    )

    return render_template(
        "admin_dashboard.html",
        total_collection=total_collection,
        total_pending=total_pending,
        batch_stats=batch_stats,
    )


# -------------------------------------------------
# BATCH CREATION
# -------------------------------------------------
@admin_bp.route("/batches", methods=["GET", "POST"])
@login_required
def manage_batches():
    if current_user.role != "admin":
        return "Access Denied", 403

    if request.method == "POST":
        new_batch = Batch(
            batch_code=request.form.get("batch_code"),
            course_name=request.form.get("course_name"),
            total_fee=int(request.form.get("total_fee")),
            start_date=datetime.strptime(
                request.form.get("start_date"), "%Y-%m-%d"
            ).date(),
            end_date=datetime.strptime(
                request.form.get("end_date"), "%Y-%m-%d"
            ).date()
            if request.form.get("end_date")
            else None,
            status="Active",
        )
        db.session.add(new_batch)
        db.session.commit()

    batches = Batch.query.order_by(Batch.created_at.desc()).all()
    return render_template("admin_batches.html", batches=batches)


# -------------------------------------------------
# PAYMENT SOURCE MASTER
# -------------------------------------------------
@admin_bp.route("/payment-sources", methods=["GET", "POST"])
@login_required
def manage_payment_sources():
    if current_user.role != "admin":
        return "Access Denied", 403

    if request.method == "POST":
        ps = PaymentSource(
            name=request.form.get("name"),
            mode=request.form.get("mode"),
            qr_image_path=request.form.get("qr_image_path")
            if request.form.get("mode") == "QR"
            else None,
            is_active=True,
        )
        db.session.add(ps)
        db.session.commit()

    payment_sources = PaymentSource.query.all()
    return render_template(
        "admin_payment_sources.html",
        payment_sources=payment_sources,
    )


# -------------------------------------------------
# PRIMARY / SECONDARY QR CONFIG (FINAL LOGIC)
# -------------------------------------------------
@admin_bp.route("/batch-payment-sources", methods=["GET", "POST"])
@login_required
def assign_payment_sources():
    if current_user.role != "admin":
        return "Access Denied", 403

    if request.method == "POST":
        batch_id = int(request.form.get("batch_id"))
        primary_qr = request.form.get("primary_qr")
        secondary_qrs = request.form.getlist("secondary_qrs")

        # clear old config
        BatchPaymentSource.query.filter_by(
            batch_id=batch_id
        ).delete()

        # CASH (always allowed)
        cash = PaymentSource.query.filter_by(mode="CASH").first()
        if cash:
            db.session.add(
                BatchPaymentSource(
                    batch_id=batch_id,
                    payment_source_id=cash.id,
                    priority=0,
                )
            )

        # PRIMARY QR
        db.session.add(
            BatchPaymentSource(
                batch_id=batch_id,
                payment_source_id=int(primary_qr),
                priority=1,
            )
        )

        # SECONDARY QRs
        for qr_id in secondary_qrs:
            if qr_id != primary_qr:
                db.session.add(
                    BatchPaymentSource(
                        batch_id=batch_id,
                        payment_source_id=int(qr_id),
                        priority=2,
                    )
                )

        db.session.commit()
        return redirect(url_for("admin.assign_payment_sources"))

    batches = Batch.query.all()
    qr_sources = PaymentSource.query.filter_by(
        mode="QR", is_active=True
    ).all()

    mappings = BatchPaymentSource.query.order_by(
        BatchPaymentSource.batch_id,
        BatchPaymentSource.priority,
    ).all()

    return render_template(
        "admin_batch_payment_sources.html",
        batches=batches,
        qr_sources=qr_sources,
        mappings=mappings,
    )


# -------------------------------------------------
# DAILY REPORT
# -------------------------------------------------
@admin_bp.route("/daily-report", methods=["GET", "POST"])
@login_required
def daily_report():
    if current_user.role != "admin":
        return "Access Denied", 403

    selected_date = date.today()

    if request.method == "POST":
        selected_date = datetime.strptime(
            request.form.get("report_date"), "%Y-%m-%d"
        ).date()

    admissions = Admission.query.filter_by(
        admission_date=selected_date
    ).all()

    payments = FeePayment.query.filter_by(
        payment_date=selected_date
    ).all()

    total_collection = sum(p.amount for p in payments)

    return render_template(
        "admin_daily_report.html",
        selected_date=selected_date,
        admissions=admissions,
        payments=payments,
        total_collection=total_collection,
    )
