# Sistema de Votaciones Seguro - Partido Republicano

Un sistema de votaciones web desarrollado con Django y MySQL, diseñado con máxima seguridad y facilidad de gestión.

## Características

### Aplicación "Voting" (Votación Pública)
- **Interfaz Amigable**: Presentación clara de votaciones con imágenes y descripciones
- **Validación de RUT**: Solo usuarios registrados en la base de datos pueden votar
- **Verificación de Email**: Se envía correo de confirmación tras emitir el voto
- **Voto Único**: Prevención de votos duplicados por RUT
- **Estadísticas en Tiempo Real**: Visualización de resultados parciales

### Aplicación "Dashboard" (Administración)
- **Login Seguro**: Autenticación de maintainers con email y contraseña
- **Gestión de Votaciones**: Crear y administrar votaciones
- **Gestión de Subjects**: Definir las opciones de votación
- **Carga de Usuarios**: Importación masiva de RUTs desde archivo Excel
- **Estadísticas Detalladas**: Gráficos y reportes de resultados
- **Gestión de Maintainers**: Control de administradores del sistema

## Instalación

### 1. Crear Base de Datos MySQL

```sql
CREATE DATABASE voting CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Clonar el repositorio y instalar dependencias

```bash
cd votings
pip install -r requirements.txt
```

### 3. Configurar la Base de Datos

Edita `votings_project/settings.py`:
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "voting",
        "USER": "root",
        "PASSWORD": "tu_password",
        "HOST": "localhost",
        "PORT": "3306",
    }
}
```

### 4. Configurar Email

En `votings_project/settings.py`:
```python
EMAIL_HOST_USER = "tu-email@gmail.com"
EMAIL_HOST_PASSWORD = "tu-app-password"
```

**Nota**: Para Gmail, usa contraseña de aplicación (no la contraseña regular).

### 5. Ejecutar Migraciones

```bash
python manage.py migrate
```

### 6. Crear Superusuario

```bash
python manage.py createsuperuser
```

### 7. Crear Datos Iniciales

```bash
python manage.py shell
```

```python
from voting.models import Role, Maintainer
from django.utils import timezone

# Crear rol
role = Role.objects.create(name="Administrador")

# Crear maintainer
maintainer = Maintainer.objects.create(
    id_role=role,
    name="Admin",
    lastname="Votaciones",
    mail="admin@votaciones.com",
    password="password123",
    is_active=True
)
```

### 8. Ejecutar el servidor

```bash
python manage.py runserver
```

Accede a:
- **Votaciones**: http://localhost:8000/
- **Dashboard**: http://localhost:8000/dashboard/

## Estructura del Proyecto

```
votings/
├── votings_project/          # Configuración principal
│   ├── settings.py           # Configuración de Django
│   ├── urls.py               # URLs principales
│   └── wsgi.py
├── voting/                   # App de votación pública
│   ├── models.py             # Modelos de datos
│   ├── views.py              # Vistas
│   ├── forms.py              # Formularios
│   ├── urls.py               # URLs
│   ├── services.py           # Servicios (email)
│   └── admin.py              # Admin de Django
├── dashboard/                # App de administración
│   ├── models.py
│   ├── views.py              # Vistas del dashboard
│   ├── forms.py              # Formularios
│   ├── urls.py               # URLs
│   ├── services.py           # Servicios (Excel)
│   ├── decorators.py         # Decoradores de autenticación
│   └── admin.py
├── templates/                # Plantillas HTML
│   ├── voting/               # Templates de votación
│   │   ├── index.html
│   │   ├── voting_detail.html
│   │   ├── vote.html
│   │   ├── success.html
│   │   ├── statistics.html
│   │   └── emails/
│   │       ├── confirmation_email.html
│   │       └── reminder_email.html
│   └── dashboard/            # Templates del dashboard
│       ├── login.html
│       ├── dashboard.html
│       ├── votings_management.html
│       ├── subjects_management.html
│       ├── user_data_management.html
│       ├── voting_statistics.html
│       ├── report.html
│       └── maintainers_management.html
├── static/                   # Archivos estáticos
│   ├── css/
│   ├── js/
│   └── img/
├── media/                    # Archivos subidos
├── requirements.txt          # Dependencias
└── manage.py
```

## Modelos de Datos

### Role
- id (PK)
- name

### Maintainer
- id (PK)
- id_role (FK → Role)
- name
- lastname
- mail (unique)
- password
- is_active
- created_at

### Voting
- id (PK)
- title
- description
- image
- start_date
- finish_date
- is_active
- created_at

### Subject
- id (PK)
- name
- description
- id_voting (FK → Voting)
- created_at

### Count
- id (PK)
- id_subject (OneToOne → Subject)
- number
- updated_at

### UserData
- id (PK)
- id_voting (FK → Voting)
- rut
- has_voted
- voted_at
- register
- created_at

### VotingRecord
- id (PK)
- id_voting (FK → Voting)
- id_subject (FK → Subject)
- user_data (FK → UserData)
- rut
- mail
- voted_at

## Flujo de Votación

1. Usuario accede a `/` (página principal de votaciones)
2. Ve votaciones disponibles y selecciona una
3. Ve los subjects/opciones de esa votación
4. Selecciona un subject para votar
5. Completa formulario con: nombre, apellido, RUT, email
6. Sistema valida que el RUT exista en user_data
7. Si es válido y no ha votado, registra el voto
8. Incrementa el contador en tabla count
9. Envía email de confirmación
10. Muestra página de éxito

## Flujo de Dashboard

1. Administrador accede a `/dashboard/login/`
2. Ingresa email y contraseña de maintainer
3. Accede al panel principal con estadísticas
4. Puede:
   - Crear nuevas votaciones
   - Gestionar subjects
   - Cargar RUTs desde Excel
   - Ver estadísticas y gráficos
   - Generar reportes
   - Gestionar otros maintainers

## Importar Usuarios desde Excel

El archivo Excel debe tener una columna llamada **rut** con los RUTs de los usuarios autorizados.

Formato recomendado:
```
rut
12345678-K
23456789-5
34567890-K
...
```

## Seguridad

- ✅ Validación de RUT chileno
- ✅ Control de acceso al dashboard
- ✅ Prevención de votos duplicados
- ✅ Verificación de email
- ✅ Transacciones atómicas
- ✅ CSRF Protection (Django)
- ✅ SQL Injection Prevention (ORM)

Para más detalles sobre la integridad y anonimato de los votos, consulta nuestra **[Auditoría de Seguridad](SECURITY.md)**.

## Dependencias Principales

- **Django**: Framework web
- **mysqlclient**: Driver MySQL
- **pandas**: Procesamiento de Excel
- **openpyxl**: Lectura/escritura Excel
- **Pillow**: Procesamiento de imágenes

## Soporte

Para dudas o problemas, contacta al equipo de desarrollo.

---

Última actualización: Marzo 2026