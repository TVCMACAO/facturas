-- Agregar columnas para rol despachador y bodega del almacén de entrega.
-- Ejecute este script en MySQL si aparece el error:
--   Unknown column 'user.assigned_delivery_point_id' in 'field list'

-- 1. Columna en user: almacén de entrega asignado al despachador
ALTER TABLE `user` ADD COLUMN `assigned_delivery_point_id` INT NULL;

-- 2. (Opcional) Si delivery_point no tiene warehouse_id, agregarlo:
-- ALTER TABLE `delivery_point` ADD COLUMN `warehouse_id` INT NULL;
