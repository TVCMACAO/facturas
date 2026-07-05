-- Migración: tabla roles y user.role_id (migración manual)
-- Ejecutar UNA vez en phpMyAdmin o con cliente MySQL. Asegúrese de tener respaldo de la BD.
-- Después de ejecutar, la aplicación usará la tabla roles y la columna user.role_id.
-- MySQL.

-- 1. Crear tabla roles
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    label VARCHAR(128) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Insertar roles
INSERT IGNORE INTO roles (code, label) VALUES
('super_admin', 'Administrador general'),
('admin', 'Administrador de empresa'),
('user', 'Usuario de ventas'),
('bodega_principal', 'Bodega principal'),
('despachador', 'Despachador'),
('minorista', 'Despachador');

-- 3. Añadir columna role_id a user
ALTER TABLE user ADD COLUMN role_id INT NULL;

-- 4. Rellenar role_id desde user.role
UPDATE user u
SET u.role_id = (SELECT id FROM roles r WHERE r.code = u.role LIMIT 1)
WHERE u.role IS NOT NULL;

-- 5. Por defecto 'user' para los que queden sin role_id
UPDATE user SET role_id = (SELECT id FROM roles WHERE code = 'user' LIMIT 1)
WHERE role_id IS NULL;

-- 6. Hacer role_id obligatorio
ALTER TABLE user MODIFY COLUMN role_id INT NOT NULL;

-- 7. Eliminar columna role
ALTER TABLE user DROP COLUMN role;

-- 8. Clave foránea
ALTER TABLE user ADD CONSTRAINT fk_user_role FOREIGN KEY (role_id) REFERENCES roles(id);
