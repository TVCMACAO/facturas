from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

class Company(db.Model):
    """Modelo para empresas/tenants"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # Nombre del negocio
    legal_name = db.Column(db.String(200))  # Razón social
    tax_id = db.Column(db.String(50))  # NIT o identificación fiscal
    address = db.Column(db.String(500))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    contact_person = db.Column(db.String(128))  # Persona responsable o de contacto
    logo_url = db.Column(db.String(500))  # URL del logo
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    __table_args__ = {'mysql_engine': 'InnoDB'}
    
    # Relaciones
    users = db.relationship('User', foreign_keys='User.company_id', backref='company', lazy='dynamic')
    clients = db.relationship('Client', foreign_keys='Client.company_id', backref='company', lazy='dynamic')
    products = db.relationship('Product', foreign_keys='Product.company_id', backref='company', lazy='dynamic')
    quotes = db.relationship('Quote', foreign_keys='Quote.company_id', backref='company', lazy='dynamic')
    invoices = db.relationship('Invoice', foreign_keys='Invoice.company_id', backref='company', lazy='dynamic')
    config = db.relationship('CompanyConfig', foreign_keys='CompanyConfig.company_id', backref='company', uselist=False)
    warehouses = db.relationship('Warehouse', foreign_keys='Warehouse.company_id', backref='company', lazy='dynamic')
    delivery_points = db.relationship('DeliveryPoint', foreign_keys='DeliveryPoint.company_id', backref='company', lazy='dynamic')
    deliveries = db.relationship('Delivery', foreign_keys='Delivery.company_id', backref='company', lazy='dynamic')
    warehouse_transfers = db.relationship('WarehouseTransfer', foreign_keys='WarehouseTransfer.company_id', backref='company', lazy='dynamic')
    receptions = db.relationship('Reception', foreign_keys='Reception.company_id', backref='company', lazy='dynamic')

class CompanyConfig(db.Model):
    """Configuración específica por empresa"""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, unique=True)
    # Email
    mail_server = db.Column(db.String(200))
    mail_port = db.Column(db.Integer, default=587)
    mail_username = db.Column(db.String(200))
    mail_password = db.Column(db.String(500))
    mail_default_sender = db.Column(db.String(200))
    # WhatsApp
    whatsapp_access_token = db.Column(db.String(500))
    whatsapp_phone_number_id = db.Column(db.String(100))
    whatsapp_business_account_id = db.Column(db.String(100))
    # Impuestos y configuración
    default_tax_rate = db.Column(db.Float, default=19.0)
    monthly_sales_target = db.Column(db.Float, default=10000.0)
    # Numeración de documentos
    quote_number_prefix = db.Column(db.String(10), default='COT')
    invoice_number_prefix = db.Column(db.String(10), default='FAC')
    credit_note_number_prefix = db.Column(db.String(10), default='NC')
    __table_args__ = {'mysql_engine': 'InnoDB'}


class Role(db.Model):
    """Roles del sistema. Códigos: super_admin, admin, user, bodega_principal, despachador."""
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), nullable=False, unique=True)
    label = db.Column(db.String(128), nullable=False)
    __table_args__ = {'mysql_engine': 'InnoDB'}

    users = db.relationship('User', backref=db.backref('role_rel', lazy='joined'), foreign_keys='User.role_id')


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    username = db.Column(db.String(64), nullable=False)  # Ya no es único globalmente
    email = db.Column(db.String(120), nullable=False)  # Ya no es único globalmente
    password_hash = db.Column(db.String(256))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, index=True)
    name = db.Column(db.String(128))
    active = db.Column(db.Boolean, default=True, nullable=False)
    assigned_delivery_point_id = db.Column(db.Integer, db.ForeignKey('delivery_point.id'), nullable=True)  # Para rol despachador
    __table_args__ = (
        db.UniqueConstraint('company_id', 'username', name='uq_user_company_username'),
        db.UniqueConstraint('company_id', 'email', name='uq_user_company_email'),
        {'mysql_engine': 'InnoDB'}
    )

    @property
    def role(self):
        """Código del rol (ej. 'super_admin', 'admin') para compatibilidad con código y plantillas."""
        return self.role_rel.code if self.role_rel else None

    @role.setter
    def role(self, code):
        r = Role.query.filter_by(code=code).first()
        self.role_id = r.id if r else self.role_id

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    document_number = db.Column(db.String(50), nullable=True)
    contact_person = db.Column(db.String(128))
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    whatsapp_number = db.Column(db.String(20)) # WhatsApp Number Field
    address = db.Column(db.String(200))
    quotes = db.relationship('Quote', backref='client', lazy='dynamic')
    invoices = db.relationship('Invoice', back_populates='client', lazy='dynamic') # New line
    __table_args__ = (
        db.UniqueConstraint('company_id', 'document_number', name='uq_client_company_document'),
        db.UniqueConstraint('company_id', 'email', name='uq_client_company_email'),
        {'mysql_engine': 'InnoDB'}
    )

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    barcode = db.Column(db.String(100))
    unit_of_sale = db.Column(db.String(20), default='unidad')  # 'unidad', 'caja', 'paquete'
    units_per_package = db.Column(db.Integer)  # ej. 12 para "caja de 12"
    __table_args__ = (
        db.UniqueConstraint('company_id', 'code', name='uq_product_company_code'),
        {'mysql_engine': 'InnoDB'}
    )

class Warehouse(db.Model):
    """Sección del centro de acopio: general o farmacia. Stock por producto en ProductWarehouseStock."""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50))
    address = db.Column(db.String(500))
    warehouse_type = db.Column(db.String(20), default='general')  # 'general', 'farmacia'; legacy: 'mayorista', 'minorista'
    active = db.Column(db.Boolean, default=True, nullable=False)
    __table_args__ = {'mysql_engine': 'InnoDB'}


class DeliveryPoint(db.Model):
    """Punto de despacho interno: destino de entregas desde el centro de acopio. warehouse_id = sección por defecto."""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50))
    address = db.Column(db.String(500))
    active = db.Column(db.Boolean, default=True, nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True)  # Bodega minorista de este almacén
    __table_args__ = {'mysql_engine': 'InnoDB'}
    warehouse = db.relationship('Warehouse', backref='delivery_points_served')
    dispatchers = db.relationship('User', backref=db.backref('assigned_delivery_point', lazy='select'), foreign_keys='User.assigned_delivery_point_id')


class ProductWarehouseStock(db.Model):
    """Stock de un producto en una bodega."""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('product_id', 'warehouse_id', name='uq_product_warehouse_stock'),
        {'mysql_engine': 'InnoDB'}
    )
    product = db.relationship('Product', backref='warehouse_stocks')
    warehouse = db.relationship('Warehouse', backref='product_stocks')


class ProductDeliveryPointStock(db.Model):
    """Stock de un producto en un almacén de entrega (punto de despacho). Cada punto tiene inventario independiente."""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    delivery_point_id = db.Column(db.Integer, db.ForeignKey('delivery_point.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('product_id', 'delivery_point_id', name='uq_product_delivery_point_stock'),
        {'mysql_engine': 'InnoDB'}
    )
    product = db.relationship('Product', backref='delivery_point_stocks')
    delivery_point = db.relationship('DeliveryPoint', backref='product_stocks')


class Delivery(db.Model):
    """Despacho: sale de una bodega hacia un almacén de entrega (entrega al menudeo)."""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False)
    delivery_point_id = db.Column(db.Integer, db.ForeignKey('delivery_point.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    delivery_number = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='borrador')  # borrador, confirmado, anulado
    notes = db.Column(db.Text)
    recipient_name = db.Column(db.String(200))
    recipient_document_number = db.Column(db.String(50))
    recipient_document_type = db.Column(db.String(20))
    delivered_at = db.Column(db.DateTime)
    __table_args__ = (
        db.UniqueConstraint('company_id', 'delivery_number', name='uq_delivery_company_number'),
        {'mysql_engine': 'InnoDB'}
    )
    warehouse = db.relationship('Warehouse', backref='deliveries')
    delivery_point = db.relationship('DeliveryPoint', backref='deliveries')
    items = db.relationship('DeliveryItem', backref='delivery', lazy='dynamic', cascade='all, delete-orphan')
    evidence = db.relationship('DeliveryEvidence', backref='delivery', lazy='dynamic', cascade='all, delete-orphan')


class DeliveryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('delivery.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product')
    __table_args__ = {'mysql_engine': 'InnoDB'}


class DeliveryEvidence(db.Model):
    """Evidencias (fotos/documentos) de una entrega."""
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('delivery.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(100))
    original_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    __table_args__ = {'mysql_engine': 'InnoDB'}


class DispatchOrder(db.Model):
    """Pedido de despacho: solicitud de productos desde un punto de despacho. Bodega prepara el despacho y al confirmar se marca recibido."""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    delivery_point_id = db.Column(db.Integer, db.ForeignKey('delivery_point.id'), nullable=False, index=True)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    order_number = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='pendiente', nullable=False)  # pendiente, en_preparacion, enviado, recibido
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    delivery_id = db.Column(db.Integer, db.ForeignKey('delivery.id'), nullable=True)  # Despacho creado desde este pedido
    __table_args__ = (
        db.UniqueConstraint('company_id', 'order_number', name='uq_dispatch_order_company_number'),
        {'mysql_engine': 'InnoDB'}
    )
    company = db.relationship('Company', backref='dispatch_orders')
    delivery_point = db.relationship('DeliveryPoint', backref='dispatch_orders')
    requested_by = db.relationship('User', backref='dispatch_orders_requested')
    delivery = db.relationship('Delivery', backref='dispatch_order', foreign_keys='DispatchOrder.delivery_id')
    items = db.relationship('DispatchOrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')


class DispatchOrderItem(db.Model):
    """Ítem de un pedido de despacho."""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('dispatch_order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product')
    __table_args__ = {'mysql_engine': 'InnoDB'}


class WarehouseTransfer(db.Model):
    """Traslado entre bodegas de la misma empresa (ej. mayorista a minorista)."""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    warehouse_origin_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False)
    warehouse_dest_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False)
    transfer_number = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='borrador')  # borrador, confirmado, anulado
    notes = db.Column(db.Text)
    __table_args__ = (
        db.UniqueConstraint('company_id', 'transfer_number', name='uq_warehouse_transfer_company_number'),
        {'mysql_engine': 'InnoDB'}
    )
    warehouse_origin = db.relationship('Warehouse', foreign_keys=[warehouse_origin_id])
    warehouse_dest = db.relationship('Warehouse', foreign_keys=[warehouse_dest_id])
    items = db.relationship('WarehouseTransferItem', backref='transfer', lazy='dynamic', cascade='all, delete-orphan')


class WarehouseTransferItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('warehouse_transfer.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)  # siempre en unidades en BD
    product = db.relationship('Product')
    __table_args__ = {'mysql_engine': 'InnoDB'}


class Reception(db.Model):
    """Recepción de mercancía en Bodega Principal Mayorista. Cada ítem se clasifica a Farmacia o Almacén General."""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    reception_number = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    guide_number = db.Column(db.String(100))  # Guía transportadora (opcional)
    status = db.Column(db.String(20), default='borrador')  # borrador, confirmado, anulado
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    received_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Usuario que confirma/recibe
    received_at = db.Column(db.DateTime, nullable=True)  # Fecha/hora de confirmación
    __table_args__ = (
        db.UniqueConstraint('company_id', 'reception_number', name='uq_reception_company_number'),
        {'mysql_engine': 'InnoDB'}
    )
    received_by = db.relationship('User', foreign_keys=[received_by_user_id])
    items = db.relationship('ReceptionItem', backref='reception', lazy='dynamic', cascade='all, delete-orphan')


class ReceptionItem(db.Model):
    """Ítem de una recepción: producto, cantidad y bodega destino (Farmacia o Almacén General)."""
    id = db.Column(db.Integer, primary_key=True)
    reception_id = db.Column(db.Integer, db.ForeignKey('reception.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False)  # Destino: Farmacia o Almacén General
    __table_args__ = {'mysql_engine': 'InnoDB'}
    product = db.relationship('Product')
    warehouse = db.relationship('Warehouse')


class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    quote_number = db.Column(db.String(20), nullable=False)
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
    __table_args__ = (
        db.UniqueConstraint('company_id', 'quote_number', name='uq_quote_company_number'),
        {'mysql_engine': 'InnoDB'}
    )

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
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    invoice_number = db.Column(db.String(20), nullable=False)
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
    __table_args__ = (
        db.UniqueConstraint('company_id', 'invoice_number', name='uq_invoice_company_number'),
        {'mysql_engine': 'InnoDB'}
    )

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
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    credit_note_number = db.Column(db.String(20), nullable=False)
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
    __table_args__ = (
        db.UniqueConstraint('company_id', 'credit_note_number', name='uq_credit_note_company_number'),
        {'mysql_engine': 'InnoDB'}
    )

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