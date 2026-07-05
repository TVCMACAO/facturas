from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FloatField, SelectField, DateField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, NumberRange, Optional, Length
from app.models import User, Client, Product, Quote, QuoteItem, Invoice, InvoiceItem, Role
from app.tenant import get_current_company_id

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recuérdame')
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(FlaskForm):
    name = StringField('Nombre Completo', validators=[DataRequired()]) # Added name field
    username = StringField('Usuario', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    password2 = PasswordField(
        'Repetir Contraseña', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrarse')


class RequestPasswordResetForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Enviar enlace de recuperación')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nueva Contraseña', validators=[DataRequired(), Length(min=6, message='La contraseña debe tener al menos 6 caracteres.')])
    password2 = PasswordField('Repetir Contraseña', validators=[DataRequired(), EqualTo('password', message='Las contraseñas deben coincidir.')])
    submit = SubmitField('Restablecer Contraseña')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Por favor, utiliza un nombre de usuario diferente.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Por favor, utiliza una dirección de email diferente.')

class ClientForm(FlaskForm):
    name = StringField('Nombre o Razón Social', validators=[DataRequired()])
    document_number = StringField('Documento (Cédula/NIT)', validators=[Optional()])
    contact_person = StringField('Persona de Contacto')
    email = StringField('Email', validators=[DataRequired()])
    phone = StringField('Teléfono')
    whatsapp_number = StringField('Número de WhatsApp') # WhatsApp Number Field
    address = StringField('Dirección')
    submit = SubmitField('Guardar Cliente')

    def validate_document_number(self, document_number):
        if document_number.data:
            client = Client.query.filter_by(document_number=document_number.data).first()
            if client:
                if hasattr(self, 'instance') and self.instance.id == client.id:
                    return
                raise ValidationError('Este número de documento ya está registrado.')

class ProductForm(FlaskForm):
    name = StringField('Nombre del Producto', validators=[DataRequired()])
    description = TextAreaField('Descripción')
    price = FloatField('Precio', validators=[DataRequired(), NumberRange(min=0, message="El precio no puede ser negativo.")])
    stock = IntegerField('Stock Inicial', validators=[NumberRange(min=0, message="El stock no puede ser negativo.")], default=0)
    barcode = StringField('Código de barras', validators=[Optional(), Length(max=100)])
    unit_of_sale = SelectField('Unidad de venta', choices=[('unidad', 'Unidad'), ('caja', 'Caja'), ('paquete', 'Paquete')], default='unidad')
    units_per_package = IntegerField('Unidades por caja/paquete', validators=[Optional(), NumberRange(min=1)], default=None)
    submit = SubmitField('Guardar Producto')

class QuoteForm(FlaskForm):
    client_id = SelectField('Cliente', coerce=int, validators=[DataRequired(message="Por favor, seleccione un cliente.")])
    date = DateField('Fecha', format='%Y-%m-%d', validators=[DataRequired()])
    tax_rate = FloatField('IVA (%)', validators=[Optional(), NumberRange(min=0, max=100, message="El IVA debe estar entre 0 y 100.")], default=19.0)
    discount_type = SelectField('Tipo de Descuento', choices=[('none', 'Sin descuento'), ('percentage', 'Porcentaje (%)'), ('amount', 'Monto fijo')], default='none', validators=[Optional()])
    discount_value = FloatField('Valor del Descuento', validators=[Optional(), NumberRange(min=0, message="El descuento no puede ser negativo.")], default=0.0)
    submit = SubmitField('Crear Cotización')

def coerce_nullable_int(x):
    if x is None or x == '':
        return None
    return int(x)

class QuoteItemForm(FlaskForm):
    product_id = SelectField('Producto', coerce=coerce_nullable_int, validators=[DataRequired(message="Por favor, seleccione un producto.")])
    quantity = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1, message="La cantidad debe ser al menos 1.")])
    unit_price = FloatField('Precio Unitario', validators=[DataRequired()])
    submit = SubmitField('Añadir Ítem')

class QuoteItemEditForm(FlaskForm):
    quantity = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1, message="La cantidad debe ser al menos 1.")])
    unit_price = FloatField('Precio Unitario', validators=[DataRequired()])
    submit = SubmitField('Guardar Cambios')

class InvoiceForm(FlaskForm):
    client_id = SelectField('Cliente', coerce=int, validators=[DataRequired(message="Por favor, seleccione un cliente.")])
    date = DateField('Fecha', format='%Y-%m-%d', validators=[DataRequired()])
    tax_rate = FloatField('IVA (%)', validators=[Optional(), NumberRange(min=0, max=100, message="El IVA debe estar entre 0 y 100.")], default=19.0)
    discount_type = SelectField('Tipo de Descuento', choices=[('none', 'Sin descuento'), ('percentage', 'Porcentaje (%)'), ('amount', 'Monto fijo')], default='none', validators=[Optional()])
    discount_value = FloatField('Valor del Descuento', validators=[Optional(), NumberRange(min=0, message="El descuento no puede ser negativo.")], default=0.0)
    submit = SubmitField('Crear Factura')

class InvoiceItemForm(FlaskForm):
    product_id = SelectField('Producto', coerce=int, validators=[DataRequired(message="Por favor, seleccione un producto.")])
    quantity = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1, message="La cantidad debe ser al menos 1.")])
    unit_price = FloatField('Precio Unitario', validators=[DataRequired()])
    submit = SubmitField('Añadir Ítem')

class CreditNoteForm(FlaskForm):
    invoice_id = SelectField('Factura', coerce=int, validators=[DataRequired(message="Por favor, seleccione una factura.")])
    date = DateField('Fecha', format='%Y-%m-%d', validators=[DataRequired()])
    reason = StringField('Motivo', validators=[DataRequired(message="Indique el motivo de la nota de crédito.")])
    tax_rate = FloatField('IVA (%)', validators=[Optional(), NumberRange(min=0, max=100, message="El IVA debe estar entre 0 y 100.")], default=19.0)
    discount_type = SelectField('Tipo de Descuento', choices=[('none', 'Sin descuento'), ('percentage', 'Porcentaje (%)'), ('amount', 'Monto fijo')], default='none', validators=[Optional()])
    discount_value = FloatField('Valor del Descuento', validators=[Optional(), NumberRange(min=0, message="El descuento no puede ser negativo.")], default=0.0)
    submit = SubmitField('Crear Nota de Crédito')

class CreditNoteItemForm(FlaskForm):
    invoice_item_id = SelectField('Ítem de Factura', coerce=coerce_nullable_int, validators=[DataRequired(message="Por favor, seleccione un ítem.")])
    quantity = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1, message="La cantidad debe ser al menos 1.")])
    submit = SubmitField('Añadir Ítem')

class InventoryForm(FlaskForm):
    product_id = SelectField('Producto', coerce=int, validators=[DataRequired(message="Por favor, seleccione un producto.")])
    new_stock = IntegerField('Nueva Cantidad en Stock', validators=[DataRequired(), NumberRange(min=0, message="El stock no puede ser negativo.")])
    submit = SubmitField('Actualizar Stock')

# Roles de negocio (fallback si la tabla roles no existe aún)
ROLE_CHOICES_BUSINESS = [
    ('admin', 'Administrador de empresa'),
    ('bodega_principal', 'Bodega principal'),
    ('despachador', 'Despachador'),
]

CODES_BUSINESS = ['admin', 'bodega_principal', 'despachador']
CODES_BUSINESS_WITH_USER = CODES_BUSINESS + ['user']


ROLE_LABELS_FALLBACK = {
    'admin': 'Administrador de empresa',
    'bodega_principal': 'Bodega principal',
    'despachador': 'Despachador',
    'user': 'Usuario de ventas',
}


def get_role_choices_from_db(codes=None):
    """Opciones de rol desde la tabla roles. codes: lista de códigos a incluir (ej. CODES_BUSINESS_WITH_USER)."""
    if codes is None:
        codes = CODES_BUSINESS
    try:
        roles = Role.query.filter(Role.code.in_(codes)).order_by(Role.id).all()
        if roles:
            return [(r.code, r.label) for r in roles]
    except Exception:
        pass
    return [(c, ROLE_LABELS_FALLBACK.get(c, c)) for c in codes]


class AdminEditUserForm(FlaskForm):
    name = StringField('Nombre Completo', validators=[DataRequired(), Length(min=2, max=128)])
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField('Rol', choices=ROLE_CHOICES_BUSINESS, validators=[DataRequired()])
    assigned_delivery_point_id = SelectField('Almacén de entrega asignado', coerce=lambda x: int(x) if x else None, validators=[Optional()])
    submit = SubmitField('Actualizar Usuario')
    
    def __init__(self, original_username, original_email, *args, **kwargs):
        super(AdminEditUserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Ese nombre de usuario ya está en uso. Por favor, elige otro.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Ese correo electrónico ya está en uso. Por favor, elige otro.')

class AdminCreateUserForm(FlaskForm):
    name = StringField('Nombre Completo', validators=[DataRequired(), Length(min=2, max=128)])
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6, message="La contraseña debe tener al menos 6 caracteres.")])
    password2 = PasswordField('Repetir Contraseña', validators=[DataRequired(), EqualTo('password', message="Las contraseñas deben coincidir.")])
    role = SelectField('Rol', choices=ROLE_CHOICES_BUSINESS, validators=[DataRequired()], default='admin')
    assigned_delivery_point_id = SelectField('Almacén de entrega asignado', coerce=lambda x: int(x) if x else None, validators=[Optional()])
    submit = SubmitField('Crear Usuario')

    def validate_username(self, username):
        company_id = get_current_company_id()
        if company_id:
            # Verificar unicidad por compañía
            user = User.query.filter_by(username=username.data, company_id=company_id).first()
            if user:
                raise ValidationError('Ese nombre de usuario ya está en uso en tu empresa. Por favor, elige otro.')
        else:
            # Fallback: verificar globalmente (no debería pasar)
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Ese nombre de usuario ya está en uso. Por favor, elige otro.')

    def validate_email(self, email):
        company_id = get_current_company_id()
        if company_id:
            # Verificar unicidad por compañía
            user = User.query.filter_by(email=email.data, company_id=company_id).first()
            if user:
                raise ValidationError('Ese correo electrónico ya está en uso en tu empresa. Por favor, elige otro.')
        else:
            # Fallback: verificar globalmente (no debería pasar)
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Ese correo electrónico ya está en uso. Por favor, elige otro.')

class UpdateQuoteStatusForm(FlaskForm):
    status = SelectField('Estado', choices=[
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
        ('facturada', 'Facturada')
    ], validators=[DataRequired()])
    submit = SubmitField('Actualizar Estado')

class InvoiceFinancialUpdateForm(FlaskForm):
    # Fields from UpdateInvoiceStatusForm
    status = SelectField('Estado', choices=[
        ('no_pagada', 'No Pagada'),
        ('parcial', 'Pago Parcial'),
        ('pagada', 'Pagada'),
        ('vencida', 'Vencida'),
        ('anulada', 'Anulada')
    ], validators=[DataRequired()])

    # Field to indicate if a new payment is being recorded
    record_new_payment = BooleanField('Registrar un nuevo pago')

    # Fields from PaymentForm, made optional initially
    amount = FloatField('Monto del Pago', validators=[Optional(), NumberRange(min=0.01)])
    payment_date = DateField('Fecha del Pago', format='%Y-%m-%d', validators=[Optional()])
    method = SelectField('Método de Pago', choices=[
        ('transferencia', 'Transferencia'),
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('otro', 'Otro')
    ], validators=[Optional()])

    submit = SubmitField('Actualizar Factura')

    def validate(self):
        if not super().validate():
            return False

        if self.record_new_payment.data:
            # If recording a new payment, make these fields required
            if not self.amount.data:
                self.amount.errors.append('El monto del pago es requerido para registrar un pago.')
                return False
            if not self.payment_date.data:
                self.payment_date.errors.append('La fecha del pago es requerida para registrar un pago.')
                return False
            if not self.method.data:
                self.method.errors.append('El método de pago es requerido para registrar un pago.')
                return False

        return True

class CompanyForm(FlaskForm):
    name = StringField('Nombre del Negocio', validators=[DataRequired(), Length(max=200)])
    legal_name = StringField('Razón Social', validators=[Optional(), Length(max=200)])
    tax_id = StringField('NIT o Identificación Fiscal', validators=[Optional(), Length(max=50)])
    address = TextAreaField('Dirección', validators=[Optional()])
    phone = StringField('Teléfono', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    website = StringField('Sitio Web', validators=[Optional(), Length(max=200)])
    contact_person = StringField('Persona Responsable / de Contacto', validators=[Optional(), Length(max=128)])
    default_tax_rate = FloatField('Tasa de IVA por Defecto (%)', validators=[Optional(), NumberRange(min=0, max=100)], default=0.0)
    monthly_sales_target = FloatField('Meta de Ventas Mensual', validators=[Optional(), NumberRange(min=0)], default=10000.0)
    quote_number_prefix = StringField('Prefijo Cotizaciones', validators=[Optional(), Length(max=10)], default='COT')
    invoice_number_prefix = StringField('Prefijo Facturas', validators=[Optional(), Length(max=10)], default='FAC')
    credit_note_number_prefix = StringField('Prefijo Notas de Crédito', validators=[Optional(), Length(max=10)], default='NC')
    submit = SubmitField('Guardar Empresa')


class CreateCompanyWithAdminForm(CompanyForm):
    """Formulario para crear empresa junto con su administrador inicial."""
    submit = SubmitField('Crear Empresa y Administrador')
    admin_name = StringField('Nombre Completo del Administrador', validators=[DataRequired(), Length(min=2, max=128)])
    admin_username = StringField('Usuario del Administrador', validators=[DataRequired(), Length(min=3, max=64)])
    admin_email = StringField('Email del Administrador', validators=[DataRequired(), Email(), Length(max=120)])
    admin_password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6, message='La contraseña debe tener al menos 6 caracteres.')])
    admin_password2 = PasswordField('Repetir Contraseña', validators=[DataRequired(), EqualTo('admin_password', message='Las contraseñas deben coincidir.')])


# Tipos de sección del centro de acopio (clínica)
WAREHOUSE_SECTION_TYPES = [('general', 'Almacén General'), ('farmacia', 'Farmacia')]

class WarehouseForm(FlaskForm):
    name = StringField('Nombre de la sección', validators=[DataRequired(), Length(max=200)])
    code = StringField('Código', validators=[Optional(), Length(max=50)])
    address = TextAreaField('Dirección', validators=[Optional()])
    warehouse_type = SelectField('Sección', choices=WAREHOUSE_SECTION_TYPES, validators=[DataRequired()])
    active = BooleanField('Activa', default=True)
    submit = SubmitField('Guardar')


class DeliveryPointForm(FlaskForm):
    name = StringField('Nombre del punto de despacho', validators=[DataRequired(), Length(max=200)])
    code = StringField('Código', validators=[Optional(), Length(max=50)])
    address = TextAreaField('Dirección', validators=[Optional()])
    warehouse_id = SelectField('Sección por defecto', coerce=lambda x: int(x) if x else None, validators=[Optional()])
    active = BooleanField('Activo', default=True)
    submit = SubmitField('Guardar')


class WarehouseTransferForm(FlaskForm):
    warehouse_origin_id = SelectField('Desde (sección)', coerce=int, validators=[DataRequired()])
    warehouse_dest_id = SelectField('Hacia (sección)', coerce=int, validators=[DataRequired()])
    date = DateField('Fecha', format='%Y-%m-%d', validators=[DataRequired()])
    notes = TextAreaField('Notas', validators=[Optional()])
    submit = SubmitField('Crear Traslado')


class WarehouseTransferItemForm(FlaskForm):
    product_id = SelectField('Producto', coerce=int, validators=[DataRequired(message='Seleccione un producto.')])
    quantity = IntegerField('Cantidad (unidades)', validators=[DataRequired(), NumberRange(min=1)])
    quantity_boxes = IntegerField('Cantidad (cajas)', validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Añadir Ítem')


class DeliveryForm(FlaskForm):
    warehouse_id = SelectField('Desde (sección)', coerce=int, validators=[DataRequired()])
    delivery_point_id = SelectField('Hacia (punto de despacho)', coerce=int, validators=[DataRequired()])
    date = DateField('Fecha', format='%Y-%m-%d', validators=[DataRequired()])
    notes = TextAreaField('Notas', validators=[Optional()])
    submit = SubmitField('Crear Despacho')


class DeliveryConfirmForm(FlaskForm):
    recipient_name = StringField('Entregado a (receptor)', validators=[Optional(), Length(max=200)])
    recipient_document_number = StringField('Número de documento', validators=[Optional(), Length(max=50)])
    recipient_document_type = SelectField('Tipo documento', choices=[('', '—'), ('cedula', 'Cédula'), ('nit', 'NIT')], validators=[Optional()])
    delivered_at = DateField('Fecha de entrega', validators=[Optional()])
    submit = SubmitField('Confirmar Entrega')


class ReceptionForm(FlaskForm):
    """Cabecera de recepción (Bodega Principal Mayorista)."""
    date = DateField('Fecha', format='%Y-%m-%d', validators=[DataRequired()])
    guide_number = StringField('Guía transportadora (opcional)', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notas', validators=[Optional()])
    submit = SubmitField('Guardar cabecera')