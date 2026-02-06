from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(64), default='user', nullable=False) # Added role field
    name = db.Column(db.String(128)) # Added name field
    __table_args__ = {'mysql_engine': 'InnoDB'}

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    document_number = db.Column(db.String(50), unique=True, nullable=True)
    contact_person = db.Column(db.String(128))
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(20))
    whatsapp_number = db.Column(db.String(20)) # WhatsApp Number Field
    address = db.Column(db.String(200))
    quotes = db.relationship('Quote', backref='client', lazy='dynamic')
    invoices = db.relationship('Invoice', back_populates='client', lazy='dynamic') # New line
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False) # Added stock field
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quote_number = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)  # Monto sin impuestos
    discount_type = db.Column(db.String(20), default='none')  # 'none', 'percentage', 'amount'
    discount_value = db.Column(db.Float, nullable=False, default=0.0)  # Valor del descuento
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)  # Monto calculado del descuento
    tax_rate = db.Column(db.Float, nullable=False, default=0.0)  # Porcentaje de IVA
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)  # Monto de IVA
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pendiente')
    items = db.relationship('QuoteItem', backref='quote', lazy='dynamic', cascade="all, delete-orphan")
    __table_args__ = {'mysql_engine': 'InnoDB'}

class QuoteItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product')
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    payment_date = db.Column(db.Date, nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'), nullable=True)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)  # Monto sin impuestos
    discount_type = db.Column(db.String(20), default='none')  # 'none', 'percentage', 'amount'
    discount_value = db.Column(db.Float, nullable=False, default=0.0)  # Valor del descuento
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)  # Monto calculado del descuento
    tax_rate = db.Column(db.Float, nullable=False, default=0.0)  # Porcentaje de IVA
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)  # Monto de IVA
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='no_pagada')
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic', cascade="all, delete-orphan")
    client = db.relationship('Client', back_populates='invoices') # Add relationship to Client for easy access
    __table_args__ = {'mysql_engine': 'InnoDB'}

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product') # Add relationship to Product for easy access
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    method = db.Column(db.String(50), nullable=False)
    invoice = db.relationship('Invoice', backref='payments', lazy=True)
    __table_args__ = {'mysql_engine': 'InnoDB'}

class InventoryMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)  # 'sale', 'purchase', 'adjustment', 'return'
    quantity = db.Column(db.Integer, nullable=False)  # positivo para entradas, negativo para salidas
    previous_stock = db.Column(db.Integer, nullable=False)
    new_stock = db.Column(db.Integer, nullable=False)
    reference_type = db.Column(db.String(20))  # 'invoice', 'quote', 'adjustment', 'credit_note'
    reference_id = db.Column(db.Integer)  # ID del documento relacionado
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    product = db.relationship('Product', backref='movements')
    user = db.relationship('User')
    __table_args__ = {'mysql_engine': 'InnoDB'}

class CreditNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credit_note_number = db.Column(db.String(20), unique=True, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(200))  # Razón de la devolución
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    discount_type = db.Column(db.String(20), default='none')
    discount_value = db.Column(db.Float, nullable=False, default=0.0)
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)
    tax_rate = db.Column(db.Float, nullable=False, default=0.0)
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')
    items = db.relationship('CreditNoteItem', backref='credit_note', lazy='dynamic', cascade="all, delete-orphan")
    invoice = db.relationship('Invoice', backref='credit_notes')
    __table_args__ = {'mysql_engine': 'InnoDB'}

class CreditNoteItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credit_note_id = db.Column(db.Integer, db.ForeignKey('credit_note.id'), nullable=False)
    invoice_item_id = db.Column(db.Integer, db.ForeignKey('invoice_item.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product')
    invoice_item = db.relationship('InvoiceItem')
    __table_args__ = {'mysql_engine': 'InnoDB'}

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'create', 'update', 'delete', 'view'
    entity_type = db.Column(db.String(50), nullable=False)  # 'invoice', 'quote', 'product', etc.
    entity_id = db.Column(db.Integer, nullable=False)
    changes = db.Column(db.Text)  # JSON con cambios realizados
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    user = db.relationship('User')
    __table_args__ = {'mysql_engine': 'InnoDB'}

class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    user = db.relationship('User', backref='password_reset_tokens')
    __table_args__ = {'mysql_engine': 'InnoDB'}