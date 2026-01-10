from datetime import datetime, date
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_code = db.Column(db.String(50), unique=True, nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    total_fee = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PaymentSource(db.Model):
    __tablename__ = "payment_sources"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mode = db.Column(db.String(10), nullable=False)
    qr_image_path = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BatchPaymentSource(db.Model):
    __tablename__ = "batch_payment_sources"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batch.id"), nullable=False)
    payment_source_id = db.Column(
        db.Integer, db.ForeignKey("payment_sources.id"), nullable=False
    )
    priority = db.Column(db.Integer, nullable=False)

    batch = db.relationship("Batch")
    payment_source = db.relationship("PaymentSource")


class Admission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("batch.id"), nullable=False)

    total_fee = db.Column(db.Integer, nullable=False)
    paid_amount = db.Column(db.Integer, default=0)
    pending_amount = db.Column(db.Integer, nullable=False)

    remarks = db.Column(db.Text)
    admission_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("Student")
    batch = db.relationship("Batch")
    payments = db.relationship("FeePayment", backref="admission")


class FeePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admission_id = db.Column(
        db.Integer, db.ForeignKey("admission.id"), nullable=False
    )
    amount = db.Column(db.Integer, nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    payment_mode = db.Column(db.String(20))
    received_in = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def generate_student_id():
    return "STD" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
