-- Migración: tablas para pedidos de despacho (punto de despacho -> bodega principal)
-- Ejecutar sobre la base de datos existente. Idempotente (CREATE TABLE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS dispatch_order (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    delivery_point_id INT NOT NULL,
    requested_by_user_id INT NULL,
    order_number VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivery_id INT NULL,
    INDEX idx_dispatch_order_company (company_id),
    INDEX idx_dispatch_order_delivery_point (delivery_point_id),
    INDEX idx_dispatch_order_status (status),
    UNIQUE KEY uq_dispatch_order_company_number (company_id, order_number),
    FOREIGN KEY (company_id) REFERENCES company(id),
    FOREIGN KEY (delivery_point_id) REFERENCES delivery_point(id),
    FOREIGN KEY (requested_by_user_id) REFERENCES user(id),
    FOREIGN KEY (delivery_id) REFERENCES delivery(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dispatch_order_item (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES dispatch_order(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
