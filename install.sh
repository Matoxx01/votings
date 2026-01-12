#!/bin/bash
# Script de instalación rápida para el sistema de votaciones

echo "🗳️  Sistema de Votaciones - Instalación"
echo "======================================"

# Paso 1: Crear base de datos
echo ""
echo "Paso 1: Crear base de datos MySQL"
echo "Ejecuta en MySQL:"
echo "CREATE DATABASE voting CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
read -p "¿Presiona Enter cuando hayas creado la base de datos..."

# Paso 2: Instalar dependencias
echo ""
echo "Paso 2: Instalando dependencias Python..."
pip install -r requirements.txt

# Paso 3: Migrar la base de datos
echo ""
echo "Paso 3: Ejecutando migraciones..."
python manage.py migrate

# Paso 4: Crear superusuario (opcional)
echo ""
echo "Paso 4: Crear superusuario para Django admin"
read -p "¿Deseas crear un superusuario? (s/n): " crear_super
if [ "$crear_super" = "s" ]; then
    python manage.py createsuperuser
fi

# Paso 5: Cargar datos iniciales
echo ""
echo "Paso 5: Cargando datos iniciales..."
python manage.py shell < scripts/init_data.py

# Paso 6: Recolectar archivos estáticos
echo ""
echo "Paso 6: Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# Finalización
echo ""
echo "✓ Instalación completada!"
echo ""
echo "Próximos pasos:"
echo "1. Configura el email en votings_project/settings.py"
echo "2. Ejecuta: python manage.py runserver"
echo "3. Accede a: http://localhost:8000"
echo ""
echo "Credenciales de prueba:"
echo "Email: admin@votaciones.com"
echo "Contraseña: admin123"
