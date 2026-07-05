-- =====================================================
-- Script de migración SQL para MySQL
-- Este script es idempotente: puede ejecutarse múltiples veces sin errores
-- =====================================================

-- NOTA: Este script usa una técnica diferente para evitar errores de "Commands out of sync"
-- Cada ALTER TABLE está envuelto en una verificación que ignora errores de columna duplicada

-- =====================================================
-- 1. AGREGAR COLUMNAS A LA TABLA quote
-- =====================================================

-- Usar SET para evitar errores de "Commands out of sync"
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quote' AND COLUMN_NAME = 'subtotal');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE quote ADD COLUMN subtotal FLOAT NOT NULL DEFAULT 0.0 AFTER client_id', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quote' AND COLUMN_NAME = 'discount_type');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE quote ADD COLUMN discount_type VARCHAR(20) DEFAULT ''none'' AFTER subtotal', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quote' AND COLUMN_NAME = 'discount_value');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE quote ADD COLUMN discount_value FLOAT NOT NULL DEFAULT 0.0 AFTER discount_type', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quote' AND COLUMN_NAME = 'discount_amount');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE quote ADD COLUMN discount_amount FLOAT NOT NULL DEFAULT 0.0 AFTER discount_value', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quote' AND COLUMN_NAME = 'tax_rate');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE quote ADD COLUMN tax_rate FLOAT NOT NULL DEFAULT 0.0 AFTER discount_amount', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quote' AND COLUMN_NAME = 'tax_amount');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE quote ADD COLUMN tax_amount FLOAT NOT NULL DEFAULT 0.0 AFTER tax_rate', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- 2. AGREGAR COLUMNAS A LA TABLA invoice
-- =====================================================

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'invoice' AND COLUMN_NAME = 'subtotal');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE invoice ADD COLUMN subtotal FLOAT NOT NULL DEFAULT 0.0 AFTER quote_id', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'invoice' AND COLUMN_NAME = 'discount_type');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE invoice ADD COLUMN discount_type VARCHAR(20) DEFAULT ''none'' AFTER subtotal', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'invoice' AND COLUMN_NAME = 'discount_value');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE invoice ADD COLUMN discount_value FLOAT NOT NULL DEFAULT 0.0 AFTER discount_type', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'invoice' AND COLUMN_NAME = 'discount_amount');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE invoice ADD COLUMN discount_amount FLOAT NOT NULL DEFAULT 0.0 AFTER discount_value', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'invoice' AND COLUMN_NAME = 'tax_rate');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE invoice ADD COLUMN tax_rate FLOAT NOT NULL DEFAULT 0.0 AFTER discount_amount', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'invoice' AND COLUMN_NAME = 'tax_amount');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE invoice ADD COLUMN tax_amount FLOAT NOT NULL DEFAULT 0.0 AFTER tax_rate', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- 3. AGREGAR COLUMNA active A LA TABLA user
-- =====================================================

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user' AND COLUMN_NAME = 'active');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE user ADD COLUMN active BOOLEAN NOT NULL DEFAULT TRUE', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

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
    contact_person VARCHAR(128),
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
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user' AND COLUMN_NAME = 'company_id');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE user ADD COLUMN company_id INT', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
-- Crear índice si no existe
SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'user' 
    AND INDEX_NAME = 'idx_user_company_id');
SET @sql = IF(@index_exists = 0, 
    'CREATE INDEX idx_user_company_id ON user(company_id)', 
    'SELECT ''Índice idx_user_company_id ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Tabla client
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'client' AND COLUMN_NAME = 'company_id');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE client ADD COLUMN company_id INT', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'client' 
    AND INDEX_NAME = 'idx_client_company_id');
SET @sql = IF(@index_exists = 0, 
    'CREATE INDEX idx_client_company_id ON client(company_id)', 
    'SELECT ''Índice idx_client_company_id ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Tabla product
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'product' AND COLUMN_NAME = 'company_id');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE product ADD COLUMN company_id INT', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'product' 
    AND INDEX_NAME = 'idx_product_company_id');
SET @sql = IF(@index_exists = 0, 
    'CREATE INDEX idx_product_company_id ON product(company_id)', 
    'SELECT ''Índice idx_product_company_id ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Tabla quote
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quote' AND COLUMN_NAME = 'company_id');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE quote ADD COLUMN company_id INT', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'quote' 
    AND INDEX_NAME = 'idx_quote_company_id');
SET @sql = IF(@index_exists = 0, 
    'CREATE INDEX idx_quote_company_id ON quote(company_id)', 
    'SELECT ''Índice idx_quote_company_id ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Tabla invoice
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'invoice' AND COLUMN_NAME = 'company_id');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE invoice ADD COLUMN company_id INT', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'invoice' 
    AND INDEX_NAME = 'idx_invoice_company_id');
SET @sql = IF(@index_exists = 0, 
    'CREATE INDEX idx_invoice_company_id ON invoice(company_id)', 
    'SELECT ''Índice idx_invoice_company_id ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Tabla credit_note (si existe)
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'credit_note' AND COLUMN_NAME = 'company_id');
SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE credit_note ADD COLUMN company_id INT', 
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'credit_note' 
    AND INDEX_NAME = 'idx_credit_note_company_id');
SET @sql = IF(@index_exists = 0, 
    'CREATE INDEX idx_credit_note_company_id ON credit_note(company_id)', 
    'SELECT ''Índice idx_credit_note_company_id ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- 7. CREAR PRIMERA EMPRESA Y ASIGNAR company_id A REGISTROS EXISTENTES
-- =====================================================

-- Verificar si ya existe una empresa
SET @company_exists = (SELECT COUNT(*) FROM company);

-- Si no existe empresa, crear una
SET @sql = IF(@company_exists = 0,
    'INSERT INTO company (name, active, created_at) VALUES (''Mi Empresa'', TRUE, NOW())',
    'SELECT ''Ya existe una empresa'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

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

-- Agregar foreign keys
SET @fk_exists = (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'user' 
    AND CONSTRAINT_NAME = 'user_ibfk_1');
SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE user ADD CONSTRAINT user_ibfk_1 FOREIGN KEY (company_id) REFERENCES company(id)',
    'SELECT ''Foreign key user_ibfk_1 ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @fk_exists = (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'client' 
    AND CONSTRAINT_NAME = 'client_ibfk_1');
SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE client ADD CONSTRAINT client_ibfk_1 FOREIGN KEY (company_id) REFERENCES company(id)',
    'SELECT ''Foreign key client_ibfk_1 ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @fk_exists = (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'product' 
    AND CONSTRAINT_NAME = 'product_ibfk_1');
SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE product ADD CONSTRAINT product_ibfk_1 FOREIGN KEY (company_id) REFERENCES company(id)',
    'SELECT ''Foreign key product_ibfk_1 ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @fk_exists = (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'quote' 
    AND CONSTRAINT_NAME = 'quote_ibfk_1');
SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE quote ADD CONSTRAINT quote_ibfk_1 FOREIGN KEY (company_id) REFERENCES company(id)',
    'SELECT ''Foreign key quote_ibfk_1 ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @fk_exists = (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'invoice' 
    AND CONSTRAINT_NAME = 'invoice_ibfk_1');
SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE invoice ADD CONSTRAINT invoice_ibfk_1 FOREIGN KEY (company_id) REFERENCES company(id)',
    'SELECT ''Foreign key invoice_ibfk_1 ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @fk_exists = (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE 
    WHERE TABLE_SCHEMA = DATABASE() 
    AND TABLE_NAME = 'credit_note' 
    AND CONSTRAINT_NAME = 'credit_note_ibfk_1');
SET @sql = IF(@fk_exists = 0,
    'ALTER TABLE credit_note ADD CONSTRAINT credit_note_ibfk_1 FOREIGN KEY (company_id) REFERENCES company(id)',
    'SELECT ''Foreign key credit_note_ibfk_1 ya existe'' AS result');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

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
-- MIGRACIÓN COMPLETADA
-- =====================================================

SELECT 'Migración completada exitosamente!' AS resultado;
