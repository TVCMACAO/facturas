-- Inventario independiente por almacén de entrega (punto de despacho).
-- Cada punto tiene su propio stock; al confirmar un despacho se descuenta de la bodega y se suma al punto.
CREATE TABLE IF NOT EXISTS product_delivery_point_stock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    delivery_point_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    UNIQUE KEY uq_product_delivery_point_stock (product_id, delivery_point_id),
    FOREIGN KEY (product_id) REFERENCES product(id),
    FOREIGN KEY (delivery_point_id) REFERENCES delivery_point(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
