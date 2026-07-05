"""
Rellena company_id NULL en cotizaciones, clientes e facturas legacy.
Ejecutar en producción: python backfill_company_ids.py
"""
import sys
from sqlalchemy import text
from app import create_app, db


def backfill_company_ids():
    app = create_app()
    with app.app_context():
        statements = [
            (
                'clientes desde primera empresa',
                """
                UPDATE client c
                SET c.company_id = (SELECT MIN(id) FROM company)
                WHERE c.company_id IS NULL
                """,
            ),
            (
                'cotizaciones desde cliente',
                """
                UPDATE quote q
                INNER JOIN client c ON q.client_id = c.id
                SET q.company_id = c.company_id
                WHERE q.company_id IS NULL AND c.company_id IS NOT NULL
                """,
            ),
            (
                'facturas desde cliente',
                """
                UPDATE invoice i
                INNER JOIN client c ON i.client_id = c.id
                SET i.company_id = c.company_id
                WHERE i.company_id IS NULL AND c.company_id IS NOT NULL
                """,
            ),
        ]

        for label, sql in statements:
            try:
                result = db.session.execute(text(sql))
                db.session.commit()
                print(f"[OK] {label}: {result.rowcount} filas actualizadas")
            except Exception as exc:
                db.session.rollback()
                print(f"[ERROR] {label}: {exc}", file=sys.stderr)
                return 1

        for table in ('quote', 'client', 'invoice'):
            count = db.session.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE company_id IS NULL")
            ).scalar()
            print(f"[INFO] {table}: {count} registros aún sin company_id")

    return 0


if __name__ == '__main__':
    sys.exit(backfill_company_ids())
