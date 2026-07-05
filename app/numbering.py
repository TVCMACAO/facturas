"""Generación centralizada de números de documentos por empresa."""
from app.models import Invoice


def _max_numeric_invoice_number(company_id):
    """Devuelve el mayor número de factura numérico existente para la empresa."""
    max_num = 0
    rows = (
        Invoice.query.filter_by(company_id=company_id)
        .with_entities(Invoice.invoice_number)
        .all()
    )
    for (invoice_number,) in rows:
        if not invoice_number:
            continue
        cleaned = str(invoice_number).strip()
        if cleaned.isdigit():
            max_num = max(max_num, int(cleaned))
    return max_num


def next_invoice_number(company_id, min_number=118):
    """
    Devuelve el siguiente número de factura para una empresa (formato 0001, mínimo 118).
    Usa el máximo numérico existente, no solo la última fila por id.
    """
    max_num = _max_numeric_invoice_number(company_id)
    next_number = max(max_num + 1, min_number)
    return str(next_number).zfill(4)
