-- ============================================================================
-- crear_base_datos.sql
-- Prepara MySQL 8 para CondoHub. Se ejecuta UNA SOLA VEZ en cada PC, con el
-- usuario administrador de MySQL (root), ANTES de "python manage.py migrate".
--
-- Cómo ejecutarlo (elige una):
--   - MySQL Workbench: abrir este archivo y presionar el rayo (Execute).
--   - Consola (PowerShell, desde la carpeta del proyecto):
--       Get-Content docs\crear_base_datos.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
--
-- Solo crea la base de datos vacía y el usuario del proyecto. Las TABLAS las
-- crea Django con "python manage.py migrate".
-- ============================================================================

-- 1) Base de datos. utf8mb4: tildes, ñ y emojis.
CREATE DATABASE IF NOT EXISTS condohub
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 2) Usuario del proyecto (así Django no usa root). Debe coincidir con el .env:
--    DB_USER=condohub   DB_PASSWORD=condohub_dev
--    Se crea para "localhost" y para "127.0.0.1" porque Django se conecta por 127.0.0.1.
CREATE USER IF NOT EXISTS 'condohub'@'localhost' IDENTIFIED BY 'condohub_dev';
CREATE USER IF NOT EXISTS 'condohub'@'127.0.0.1' IDENTIFIED BY 'condohub_dev';

-- 3) Permisos: control total, pero SOLO sobre la base condohub...
GRANT ALL PRIVILEGES ON condohub.* TO 'condohub'@'localhost';
GRANT ALL PRIVILEGES ON condohub.* TO 'condohub'@'127.0.0.1';

-- 4) ...y sobre la base temporal que crea "python manage.py test".
GRANT ALL PRIVILEGES ON `test\_condohub`.* TO 'condohub'@'localhost';
GRANT ALL PRIVILEGES ON `test\_condohub`.* TO 'condohub'@'127.0.0.1';

FLUSH PRIVILEGES;
