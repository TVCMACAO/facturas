-- Agregar columna contact_person a la tabla company
-- Ejecutar este script en la MISMA base de datos que usa la aplicación Flask
-- (phpMyAdmin, MySQL Workbench, o: mysql -u usuario -p nombre_bd < add_contact_person_to_company.sql)

ALTER TABLE company 
ADD COLUMN contact_person VARCHAR(128) NULL AFTER website;
