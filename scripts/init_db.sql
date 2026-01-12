-- Script para inicializar la base de datos con datos iniciales
-- Ejecutar después de: python manage.py migrate

-- Nota: Este script es informativo. Los roles deben crearse desde Django
-- python manage.py shell
-- from voting.models import Role, Maintainer
-- role = Role.objects.create(name="Administrador")
-- maintainer = Maintainer.objects.create(
--     id_role=role,
--     name="Admin",
--     lastname="Votaciones",
--     mail="admin@votaciones.com",
--     password="password123"
-- )

-- O usar el siguiente SQL directamente después de las migraciones:

INSERT INTO voting_role (name, created_at) 
VALUES ('Administrador', NOW());

INSERT INTO voting_role (name, created_at) 
VALUES ('Moderador', NOW());

INSERT INTO voting_role (name, created_at) 
VALUES ('Auditor', NOW());

-- Para crear un maintainer, primero obtén el ID del rol creado
-- SELECT id FROM voting_role WHERE name = 'Administrador';

-- Luego:
-- INSERT INTO voting_maintainer (id_role_id, name, lastname, mail, password, is_active, created_at)
-- VALUES (1, 'Admin', 'Sistema', 'admin@votaciones.com', 'password123', 1, NOW());
