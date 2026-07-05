"""Generación centralizada de números de documentos por empresa."""
from app.models import Invoice


def next_invoice_number(company_id, min_number=118):
    """
    Devuelve el siguiente número de factura para una empresa (formato 0001, mínimo 118).
    """
    last_invoice = (
        Invoice.query.filter_by(company_id=company_id)
        .order_by(Invoice.id.desc())
        .first()
    )
    if last_invoice and last_invoice.invoice_number.isdigit():
        next_number = int(last_invoice.invoice_number) + 1
    else:
        next_number = 1
    if next_number < min_number:
        next_number = min_number
    return str(next_number).zfill(4)
