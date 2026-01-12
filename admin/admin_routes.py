from flask import Blueprint, render_template, request, redirect, url_for, abort
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
        abort(403)

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
# PAYMENT SOURCE MASTER
# -------------------------------------------------
@admin_bp.route("/payment-sources", methods=["GET", "POST"])
@login_required
def manage_payment_sources():
    if current_user.role != "admin":
        abort(403)

    if request.method == "POST":
        name = request.form.get("name")
        mode = request.form.get("mode")

        if not name or not mode:
            abort(400)

        ps = PaymentSource(
            name=name,
            mode=mode,
            qr_image_path=request.form.get("qr_image_path")
            if mode == "QR"
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
# MULTI PAYMENT CONFIG (CORRECTED & SAFE)
# -------------------------------------------------
@admin_bp.route("/batch-payment-sources", methods=["GET", "POST"])
@login_required
def assign_payment_sources():
    if current_user.role != "admin":
        abort(403)

    if request.method == "POST":
        batch_id = request.form.get("batch_id")
        payment_source_ids = request.form.getlist("payment_sources")

        # HARD VALIDATION (non-negotiable)
        if not batch_id:
            abort(400, "Batch is required")

        if not payment_source_ids:
            abort(400, "At least one payment source is required")

        batch_id = int(batch_id)

        # Remove old config
        BatchPaymentSource.query.filter_by(
            batch_id=batch_id
        ).delete()

        # Normalize order → priority = index
        for priority, ps_id in enumerate(payment_source_ids):
            db.session.add(
                BatchPaymentSource(
                    batch_id=batch_id,
                    payment_source_id=int(ps_id),
                    priority=priority,
                )
            )

        db.session.commit()
        return redirect(url_for("admin.assign_payment_sources"))

    batches = Batch.query.order_by(Batch.batch_code).all()
    payment_sources = PaymentSource.query.filter_by(
        is_active=True
    ).order_by(PaymentSource.name).all()

    mappings = BatchPaymentSource.query.order_by(
        BatchPaymentSource.batch_id,
        BatchPaymentSource.priority,
    ).all()

    return render_template(
        "admin_batch_payment_sources.html",
        batches=batches,
        payment_sources=payment_sources,
        mappings=mappings,
    )


# -------------------------------------------------
# BATCH MANAGEMENT
# -------------------------------------------------
@admin_bp.route("/batches", methods=["GET", "POST"])
@login_required
def manage_batches():
    if current_user.role != "admin":
        abort(403)

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

    batches = Batch.query.order_by(
        Batch.created_at.desc()
    ).all()
    return render_template(
        "admin_batches.html",
        batches=batches
    )


# -------------------------------------------------
# DAILY REPORT
# -------------------------------------------------
@admin_bp.route("/daily-report", methods=["GET", "POST"])
@login_required
def daily_report():
    if current_user.role != "admin":
        abort(403)

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
# -------------------------------------------------
# DELETE BATCH (ADMIN ONLY)
# -------------------------------------------------
@admin_bp.route("/batches/<int:batch_id>/delete", methods=["POST"])
@login_required
def delete_batch(batch_id):
    if current_user.role != "admin":
        abort(403)

    batch = Batch.query.get_or_404(batch_id)

    # HARD SAFETY: delete dependent records first
    # 1. Remove batch-payment mappings
    BatchPaymentSource.query.filter_by(
        batch_id=batch.id
    ).delete()

    # 2. Get admissions linked to this batch
    admissions = Admission.query.filter_by(
        batch_id=batch.id
    ).all()

    admission_ids = [a.id for a in admissions]

    # 3. Delete fee payments linked to those admissions
    if admission_ids:
        FeePayment.query.filter(
            FeePayment.admission_id.in_(admission_ids)
        ).delete(synchronize_session=False)

    # 4. Delete admissions
    Admission.query.filter_by(
        batch_id=batch.id
    ).delete()

    # 5. Delete batch itself
    db.session.delete(batch)

    db.session.commit()

    return redirect(url_for("admin.manage_batches"))
