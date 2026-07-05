# Depuración: 500 en convert_to_invoice — RESUELTO

**Estado:** Corregido en julio 2026.

## Causa

1. Falta de `company_id` al crear `Invoice` (corregido previamente).
2. Numeración de factura sin filtrar por empresa → duplicado en `uq_invoice_company_number` → 500.

## Solución aplicada

- `app/numbering.py`: `next_invoice_number(company_id)`.
- `convert_to_invoice` usa el helper y filtra por empresa.
- Conversión cambiada a **POST** con CSRF (GET antiguo redirige con mensaje).
- Rollback y mensaje amigable en `IntegrityError`.

## Verificación

```bash
python -m pytest tests/ -q
```

Probar manualmente: cotización → Convertir a factura → ver factura sin error 500.
