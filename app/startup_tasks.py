"""Tareas idempotentes al iniciar la aplicación."""
from sqlalchemy import text


def backfill_null_company_ids(app):
    """Rellena company_id NULL en clientes y cotizaciones legacy."""
    from app import db

    if db.engine.dialect.name != 'mysql':
        return

    try:
        db.session.execute(text("""
            UPDATE client
            SET company_id = (SELECT MIN(id) FROM company)
            WHERE company_id IS NULL
              AND EXISTS (SELECT 1 FROM company)
        """))
        db.session.execute(text("""
            UPDATE quote q
            INNER JOIN client c ON q.client_id = c.id
            SET q.company_id = c.company_id
            WHERE q.company_id IS NULL AND c.company_id IS NOT NULL
        """))
        db.session.execute(text("""
            UPDATE invoice i
            INNER JOIN client c ON i.client_id = c.id
            SET i.company_id = c.company_id
            WHERE i.company_id IS NULL AND c.company_id IS NOT NULL
        """))
        db.session.commit()
        app.logger.info('Startup backfill: company_id actualizado en registros legacy')
    except Exception as exc:
        db.session.rollback()
        app.logger.warning('Startup backfill omitido: %s', exc)
