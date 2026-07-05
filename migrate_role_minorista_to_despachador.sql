-- Migración: fusionar rol minorista con despachador.
-- Ejecutar una sola vez para que todos los usuarios con rol 'minorista' pasen a 'despachador'.
-- El código ya no usa el rol 'minorista'; solo 'despachador'.

UPDATE user SET role = 'despachador' WHERE role = 'minorista';
