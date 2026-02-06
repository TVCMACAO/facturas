-- Script de migración para agregar nuevas columnas y tablas
-- Ejecutar este script en MySQL para actualizar la base de datos

-- Agregar columnas a la tabla quote
ALTER TABLE quote 
ADD COLUMN subtotal FLOAT NOT NULL DEFAULT 0.0 AFTER client_id,
ADD COLUMN discount_type VARCHAR(20) DEFAULT 'none' AFTER subtotal,
ADD COLUMN discount_value FLOAT NOT NULL DEFAULT 0.0 AFTER discount_type,
ADD COLUMN discount_amount FLOAT NOT NULL DEFAULT 0.0 AFTER discount_value,
ADD COLUMN tax_rate FLOAT NOT NULL DEFAULT 0.0 AFTER discount_amount,
ADD COLUMN tax_amount FLOAT NOT NULL DEFAULT 0.0 AFTER tax_rate;

-- Agregar columnas a la tabla invoice
ALTER TABLE invoice 
ADD COLUMN subtotal FLOAT NOT NULL DEFAULT 0.0 AFTER quote_id,
ADD COLUMN discount_type VARCHAR(20) DEFAULT 'none' AFTER subtotal,
ADD COLUMN discount_value FLOAT NOT NULL DEFAULT 0.0 AFTER discount_type,
ADD COLUMN discount_amount FLOAT NOT NULL DEFAULT 0.0 AFTER discount_value,
ADD COLUMN tax_rate FLOAT NOT NULL DEFAULT 0.0 AFTER discount_amount,
ADD COLUMN tax_amount FLOAT NOT NULL DEFAULT 0.0 AFTER tax_rate;

-- Crear tabla inventory_movement si no existe
CREATE TABLE IF NOT EXISTS inventory_movement (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    movement_type VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    previous_stock INT NOT NULL,
    new_stock INT NOT NULL,
    reference_type VARCHAR(20),
    reference_id INT,
    user_id INT,
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES product(id),
    FOREIGN KEY (user_id) REFERENCES user(id),
    INDEX idx_product_id (product_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- Crear tabla credit_note si no existe
CREATE TABLE IF NOT EXISTS credit_note (
    id INT AUTO_INCREMENT PRIMARY KEY,
    credit_note_number VARCHAR(20) UNIQUE NOT NULL,
    invoice_id INT NOT NULL,
    date DATETIME NOT NULL,
    reason VARCHAR(200),
    subtotal FLOAT NOT NULL DEFAULT 0.0,
    discount_type VARCHAR(20) DEFAULT 'none',
    discount_value FLOAT NOT NULL DEFAULT 0.0,
    discount_amount FLOAT NOT NULL DEFAULT 0.0,
    tax_rate FLOAT NOT NULL DEFAULT 0.0,
    tax_amount FLOAT NOT NULL DEFAULT 0.0,
    total_amount FLOAT NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    FOREIGN KEY (invoice_id) REFERENCES invoice(id),
    INDEX idx_invoice_id (invoice_id),
    INDEX idx_date (date)
) ENGINE=InnoDB;

-- Crear tabla credit_note_item si no existe
CREATE TABLE IF NOT EXISTS credit_note_item (
    id INT AUTO_INCREMENT PRIMARY KEY,
    credit_note_id INT NOT NULL,
    invoice_item_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price FLOAT NOT NULL,
    total_price FLOAT NOT NULL,
    FOREIGN KEY (credit_note_id) REFERENCES credit_note(id) ON DELETE CASCADE,
    FOREIGN KEY (invoice_item_id) REFERENCES invoice_item(id),
    FOREIGN KEY (product_id) REFERENCES product(id),
    INDEX idx_credit_note_id (credit_note_id)
) ENGINE=InnoDB;

-- Crear tabla audit_log si no existe
CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT NOT NULL,
    changes TEXT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(200),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id),
    INDEX idx_user_id (user_id),
    INDEX idx_entity_type (entity_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- Actualizar valores existentes: calcular subtotal y tax para cotizaciones existentes
UPDATE quote 
SET subtotal = total_amount,
    tax_rate = 0.0,
    tax_amount = 0.0
WHERE subtotal = 0.0 AND total_amount > 0;

-- Actualizar valores existentes: calcular subtotal y tax para facturas existentes
UPDATE invoice 
SET subtotal = total_amount,
    tax_rate = 0.0,
    tax_amount = 0.0
WHERE subtotal = 0.0 AND total_amount > 0;
