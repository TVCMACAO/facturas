from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FloatField, SelectField, DateField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, NumberRange, Optional, Length
from app.models import User, Client, Product, Quote, QuoteItem, Invoice, InvoiceItem # Added Invoice, InvoiceItem

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

class InventoryForm(FlaskForm):
    product_id = SelectField('Producto', coerce=int, validators=[DataRequired(message="Por favor, seleccione un producto.")])
    new_stock = IntegerField('Nueva Cantidad en Stock', validators=[DataRequired(), NumberRange(min=0, message="El stock no puede ser negativo.")])
    submit = SubmitField('Actualizar Stock')

class AdminEditUserForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Rol', choices=[('user', 'Usuario'), ('admin', 'Administrador')], validators=[DataRequired()])
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
            if not self.payment_date.data:
                self.payment_date.errors.append('La fecha del pago es requerida para registrar un pago.')
            if not self.method.data:
                self.method.errors.append('El método de pago es requerido para registrar un pago.')

            if self.amount.errors or self.payment_date.errors or self.method.errors:
                return False
        
        # If status is 'pagada' but no payment is recorded, ensure payment_date is set
        if self.status.data == 'pagada' and not self.record_new_payment.data and not self.payment_date.data:
            self.payment_date.errors.append('La fecha de pago es requerida si el estado es "Pagada" y no se registra un nuevo pago.')
            return False

        return True

class CreditNoteForm(FlaskForm):
    invoice_id = SelectField('Factura', coerce=int, validators=[DataRequired(message="Por favor, seleccione una factura.")])
    date = DateField('Fecha', format='%Y-%m-%d', validators=[DataRequired()])
    reason = StringField('Razón de la Devolución', validators=[Optional(), Length(max=200)])
    tax_rate = FloatField('IVA (%)', validators=[Optional(), NumberRange(min=0, max=100, message="El IVA debe estar entre 0 y 100.")], default=19.0)
    discount_type = SelectField('Tipo de Descuento', choices=[('none', 'Sin descuento'), ('percentage', 'Porcentaje (%)'), ('amount', 'Monto fijo')], default='none', validators=[Optional()])
    discount_value = FloatField('Valor del Descuento', validators=[Optional(), NumberRange(min=0, message="El descuento no puede ser negativo.")], default=0.0)
    submit = SubmitField('Crear Nota de Crédito')

class CreditNoteItemForm(FlaskForm):
    invoice_item_id = SelectField('Ítem de Factura', coerce=int, validators=[DataRequired(message="Por favor, seleccione un ítem.")])
    quantity = IntegerField('Cantidad a Devolver', validators=[DataRequired(), NumberRange(min=1, message="La cantidad debe ser al menos 1.")])
    submit = SubmitField('Añadir Ítem')

class RequestPasswordResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Enviar Enlace de Recuperación')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nueva Contraseña', validators=[DataRequired(), Length(min=6, message="La contraseña debe tener al menos 6 caracteres.")])
    password2 = PasswordField(
        'Confirmar Contraseña', validators=[DataRequired(), EqualTo('password', message='Las contraseñas no coinciden.')])
    submit = SubmitField('Restablecer Contraseña')
