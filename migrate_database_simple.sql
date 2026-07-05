-- =====================================================
-- Script de migración SQL para MySQL (Versión Simple)
-- Este script puede ejecutarse múltiples veces
-- Si una columna ya existe, simplemente ignora el error
-- =====================================================

-- IMPORTANTE: Si phpMyAdmin muestra errores de "columna duplicada",
-- simplemente ignóralos y continúa. El script seguirá funcionando.

-- =====================================================
-- 1. AGREGAR COLUMNAS A LA TABLA quote
-- =====================================================

ALTER TABLE quote ADD COLUMN subtotal FLOAT NOT NULL DEFAULT 0.0 AFTER client_id;
ALTER TABLE quote ADD COLUMN discount_type VARCHAR(20) DEFAULT 'none' AFTER subtotal;
ALTER TABLE quote ADD COLUMN discount_value FLOAT NOT NULL DEFAULT 0.0 AFTER discount_type;
ALTER TABLE quote ADD COLUMN discount_amount FLOAT NOT NULL DEFAULT 0.0 AFTER discount_value;
ALTER TABLE quote ADD COLUMN tax_rate FLOAT NOT NULL DEFAULT 0.0 AFTER discount_amount;
ALTER TABLE quote ADD COLUMN tax_amount FLOAT NOT NULL DEFAULT 0.0 AFTER tax_rate;

-- =====================================================
-- 2. AGREGAR COLUMNAS A LA TABLA invoice
-- =====================================================

ALTER TABLE invoice ADD COLUMN subtotal FLOAT NOT NULL DEFAULT 0.0 AFTER quote_id;
ALTER TABLE invoice ADD COLUMN discount_type VARCHAR(20) DEFAULT 'none' AFTER subtotal;
ALTER TABLE invoice ADD COLUMN discount_value FLOAT NOT NULL DEFAULT 0.0 AFTER discount_type;
ALTER TABLE invoice ADD COLUMN discount_amount FLOAT NOT NULL DEFAULT 0.0 AFTER discount_value;
ALTER TABLE invoice ADD COLUMN tax_rate FLOAT NOT NULL DEFAULT 0.0 AFTER discount_amount;
ALTER TABLE invoice ADD COLUMN tax_amount FLOAT NOT NULL DEFAULT 0.0 AFTER tax_rate;

-- =====================================================
-- 3. AGREGAR COLUMNA active A LA TABLA user
-- =====================================================

ALTER TABLE user ADD COLUMN active BOOLEAN NOT NULL DEFAULT TRUE;

-- Actualizar usuarios existentes como activos
UPDATE user SET active = TRUE WHERE active IS NULL OR active = FALSE;

-- =====================================================
-- 4. CREAR TABLA company (si no existe)
-- =====================================================

CREATE TABLE IF NOT EXISTS company (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    legal_name VARCHAR(200),
    tax_id VARCHAR(50),
    address VARCHAR(500),
    phone VARCHAR(20),
    email VARCHAR(120),
    website VARCHAR(200),
    logo_url VARCHAR(500),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INT,
    FOREIGN KEY (created_by) REFERENCES user(id),
    INDEX idx_company_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 5. CREAR TABLA company_config (si no existe)
-- =====================================================

CREATE TABLE IF NOT EXISTS company_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL UNIQUE,
    mail_server VARCHAR(200),
    mail_port INT DEFAULT 587,
    mail_username VARCHAR(200),
    mail_password VARCHAR(500),
    mail_default_sender VARCHAR(200),
    whatsapp_access_token VARCHAR(500),
    whatsapp_phone_number_id VARCHAR(100),
    whatsapp_business_account_id VARCHAR(100),
    default_tax_rate FLOAT DEFAULT 19.0,
    monthly_sales_target FLOAT DEFAULT 10000.0,
    quote_number_prefix VARCHAR(10) DEFAULT 'COT',
    invoice_number_prefix VARCHAR(10) DEFAULT 'FAC',
    credit_note_number_prefix VARCHAR(10) DEFAULT 'NC',
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
    INDEX idx_company_config_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 6. AGREGAR company_id A TODAS LAS TABLAS
-- =====================================================

-- Tabla user
ALTER TABLE user ADD COLUMN company_id INT;
CREATE INDEX idx_user_company_id ON user(company_id);

-- Tabla client
ALTER TABLE client ADD COLUMN company_id INT;
CREATE INDEX idx_client_company_id ON client(company_id);

-- Tabla product
ALTER TABLE product ADD COLUMN company_id INT;
CREATE INDEX idx_product_company_id ON product(company_id);

-- Tabla quote
ALTER TABLE quote ADD COLUMN company_id INT;
CREATE INDEX idx_quote_company_id ON quote(company_id);

-- Tabla invoice
ALTER TABLE invoice ADD COLUMN company_id INT;
CREATE INDEX idx_invoice_company_id ON invoice(company_id);

-- Tabla credit_note (si existe)
ALTER TABLE credit_note ADD COLUMN company_id INT;
CREATE INDEX idx_credit_note_company_id ON credit_note(company_id);

-- =====================================================
-- 7. CREAR PRIMERA EMPRESA Y ASIGNAR company_id
-- =====================================================

-- Crear primera empresa si no existe
INSERT INTO company (name, active, created_at)
SELECT 'Mi Empresa', TRUE, NOW()
WHERE NOT EXISTS (SELECT 1 FROM company LIMIT 1);

-- Obtener el ID de la primera empresa
SET @first_company_id = (SELECT id FROM company LIMIT 1);

-- Asignar company_id a todos los registros existentes que no lo tengan
UPDATE user SET company_id = @first_company_id WHERE company_id IS NULL;
UPDATE client SET company_id = @first_company_id WHERE company_id IS NULL;
UPDATE product SET company_id = @first_company_id WHERE company_id IS NULL;
UPDATE quote SET company_id = @first_company_id WHERE company_id IS NULL;
UPDATE invoice SET company_id = @first_company_id WHERE company_id IS NULL;
UPDATE credit_note SET company_id = @first_company_id WHERE company_id IS NULL;

-- Hacer company_id NOT NULL en todas las tablas
ALTER TABLE user MODIFY COLUMN company_id INT NOT NULL;
ALTER TABLE client MODIFY COLUMN company_id INT NOT NULL;
ALTER TABLE product MODIFY COLUMN company_id INT NOT NULL;
ALTER TABLE quote MODIFY COLUMN company_id INT NOT NULL;
ALTER TABLE invoice MODIFY COLUMN company_id INT NOT NULL;
ALTER TABLE credit_note MODIFY COLUMN company_id INT NOT NULL;

-- Agregar foreign keys (ignorar si ya existen)
ALTER TABLE user ADD CONSTRAINT user_ibfk_company FOREIGN KEY (company_id) REFERENCES company(id);
ALTER TABLE client ADD CONSTRAINT client_ibfk_company FOREIGN KEY (company_id) REFERENCES company(id);
ALTER TABLE product ADD CONSTRAINT product_ibfk_company FOREIGN KEY (company_id) REFERENCES company(id);
ALTER TABLE quote ADD CONSTRAINT quote_ibfk_company FOREIGN KEY (company_id) REFERENCES company(id);
ALTER TABLE invoice ADD CONSTRAINT invoice_ibfk_company FOREIGN KEY (company_id) REFERENCES company(id);
ALTER TABLE credit_note ADD CONSTRAINT credit_note_ibfk_company FOREIGN KEY (company_id) REFERENCES company(id);

-- =====================================================
-- 8. CREAR COMPANY_CONFIG PARA LA PRIMERA EMPRESA
-- =====================================================

INSERT INTO company_config (company_id, default_tax_rate, monthly_sales_target, quote_number_prefix, invoice_number_prefix, credit_note_number_prefix)
SELECT @first_company_id, 19.0, 10000.0, 'COT', 'FAC', 'NC'
WHERE NOT EXISTS (SELECT 1 FROM company_config WHERE company_id = @first_company_id);

-- =====================================================
-- 9. ACTUALIZAR VALORES EXISTENTES EN quote E invoice
-- =====================================================

UPDATE quote SET subtotal = total_amount, tax_rate = 0.0, tax_amount = 0.0 
WHERE subtotal = 0.0 AND total_amount > 0;

UPDATE invoice SET subtotal = total_amount, tax_rate = 0.0, tax_amount = 0.0 
WHERE subtotal = 0.0 AND total_amount > 0;

-- =====================================================
-- 10. PERMITIR MISMO USERNAME EN DISTINTAS EMPRESAS
-- =====================================================
-- Elimina el índice único antiguo que hacía username único en toda la tabla.
-- La aplicación usa unicidad por (company_id, username).
-- Si el índice no existe, MySQL puede mostrar error; ignóralo o ejecuta:
--   python fix_user_username_index.py

DROP INDEX ix_user_username ON user;

-- =====================================================
-- MIGRACIÓN COMPLETADA
-- =====================================================

SELECT 'Migración completada exitosamente!' AS resultado;
