"""
Script para inicializar datos de prueba en la base de datos
Ejecutar con: python manage.py shell < scripts/init_data.py
O manualmente en: python manage.py shell y copiar el contenido
"""

from voting.models import Role, Maintainer, Voting, Subject, Count, UserData
from django.utils import timezone
from datetime import timedelta

# Crear roles
print("Creando roles...")
admin_role, _ = Role.objects.get_or_create(name="Administrador")
moderator_role, _ = Role.objects.get_or_create(name="Moderador")
auditor_role, _ = Role.objects.get_or_create(name="Auditor")
print("✓ Roles creados")

# Crear maintainers
print("Creando maintainers...")
maintainer, created = Maintainer.objects.get_or_create(
    mail="matias@barrioslira.com",
    defaults={
        "id_role": admin_role,
        "name": "admin",
        "lastname": "",
        "password": "1234",
        "is_active": True,
    }
)
if created:
    print(f"✓ Maintainer creado: {maintainer.name} {maintainer.lastname}")
else:
    print("ℹ Maintainer ya existe")

# Crear votación de prueba
print("Creando votación de prueba...")
start_date = timezone.now() + timedelta(hours=1)
end_date = start_date + timedelta(hours=24)

voting, created = Voting.objects.get_or_create(
    title="Votación de Prueba",
    defaults={
        "description": "Esta es una votación de prueba del sistema",
        "start_date": start_date,
        "finish_date": end_date,
        "is_active": True,
    }
)
if created:
    print(f"✓ Votación creada: {voting.title}")
else:
    print("ℹ Votación ya existe")

# Crear subjects de prueba
print("Creando subjects...")
subjects_data = [
    {"name": "Opción A", "description": "Primera opción de votación"},
    {"name": "Opción B", "description": "Segunda opción de votación"},
    {"name": "Opción C", "description": "Tercera opción de votación"},
]

for subject_data in subjects_data:
    subject, created = Subject.objects.get_or_create(
        name=subject_data["name"],
        id_voting=voting,
        defaults={"description": subject_data["description"]}
    )
    if created:
        # Crear contador asociado
        Count.objects.get_or_create(id_subject=subject, defaults={"number": 0})
        print(f"✓ Subject creado: {subject.name}")
    else:
        print(f"ℹ Subject ya existe: {subject.name}")

# Crear usuarios de prueba para votar
print("Creando usuarios de prueba...")
users_data = [
    "12345678-K",
    "23456789-5",
    "34567890-K",
    "45678901-2",
    "56789012-K",
]

for rut in users_data:
    user_data, created = UserData.objects.get_or_create(
        rut=rut,
        id_voting=voting,
        defaults={"register": False, "has_voted": False}
    )
    if created:
        print(f"✓ Usuario creado: {rut}")
    else:
        print(f"ℹ Usuario ya existe: {rut}")

print("\n✓ Datos de prueba inicializados correctamente")