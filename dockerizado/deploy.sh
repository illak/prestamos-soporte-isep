#!/bin/bash

# Script de despliegue para Sistema de Préstamos de Equipos
# Uso: ./deploy.sh [desarrollo|produccion]

set -e  # Salir si hay errores

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logs coloridos
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar que Docker esté instalado
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker no está instalado. Instálalo desde https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose no está disponible"
        exit 1
    fi
    
    log_success "Docker y Docker Compose están disponibles"
}

# Verificar archivos necesarios
check_files() {
    local files=("app.py" "requirements.txt" "Dockerfile" "docker-compose.yml")
    
    for file in "${files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Archivo requerido no encontrado: $file"
            exit 1
        fi
    done
    
    log_success "Todos los archivos necesarios están presentes"
}

# Crear directorio de datos si no existe
setup_data_dir() {
    if [[ ! -d "data" ]]; then
        mkdir -p data
        log_info "Directorio 'data' creado para persistencia de base de datos"
    fi
}

# Despliegue para desarrollo
deploy_development() {
    log_info "Desplegando en modo DESARROLLO..."
    
    # Construir imagen
    log_info "Construyendo imagen Docker..."
    docker-compose build
    
    # Levantar servicios
    log_info "Iniciando servicios..."
    docker-compose up -d
    
    # Esperar a que la aplicación esté lista
    log_info "Esperando a que la aplicación esté lista..."
    sleep 10
    
    # Verificar que esté funcionando
    if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
        log_success "¡Aplicación desplegada exitosamente!"
        log_info "Accede en: http://localhost:8501"
    else
        log_error "La aplicación no responde correctamente"
        docker-compose logs --tail=50
        exit 1
    fi
}

# Despliegue para producción
deploy_production() {
    log_info "Desplegando en modo PRODUCCIÓN..."
    
    # Solicitar URL de producción
    read -p "Ingresa la URL de producción (ej: https://equipos.miempresa.com): " PROD_URL
    
    if [[ -z "$PROD_URL" ]]; then
        log_error "URL de producción es requerida"
        exit 1
    fi
    
    # Crear archivo de configuración de producción
    cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  equipos-app:
    build: .
    container_name: sistema-equipos-prod
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./equipos.db:/app/equipos.db
    environment:
      - BASE_URL=$PROD_URL
      - STREAMLIT_SERVER_ENABLE_CORS=false
      - STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF

    log_info "Archivo de configuración de producción creado"
    
    # Construir imagen
    log_info "Construyendo imagen Docker para producción..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Levantar servicios
    log_info "Iniciando servicios de producción..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Verificar despliegue
    log_info "Esperando a que la aplicación esté lista..."
    sleep 15
    
    if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
        log_success "¡Aplicación desplegada en producción!"
        log_info "URL configurada: $PROD_URL"
        log_info "Puerto local: http://localhost:8501"
        log_warning "Recuerda configurar tu proxy reverso (Nginx/Apache) para apuntar a este contenedor"
    else
        log_error "La aplicación no responde correctamente"
        docker-compose -f docker-compose.prod.yml logs --tail=50
        exit 1
    fi
}

# Función para mostrar estado
show_status() {
    log_info "Estado actual de los contenedores:"
    docker-compose ps
    echo ""
    
    log_info "Logs recientes:"
    docker-compose logs --tail=20
}

# Función para crear backup
create_backup() {
    local backup_name="backup-equipos-$(date +%Y%m%d-%H%M%S).db"
    
    if docker-compose ps | grep -q "sistema-equipos"; then
        docker cp sistema-equipos:/app/equipos.db "./$backup_name"
        log_success "Backup creado: $backup_name"
    else
        if [[ -f "equipos.db" ]]; then
            cp equipos.db "$backup_name"
            log_success "Backup creado: $backup_name"
        else
            log_error "No se encontró base de datos para respaldar"
            exit 1
        fi
    fi
}

# Función para limpiar deployment
cleanup() {
    log_warning "¿Estás seguro de que quieres eliminar todos los contenedores y datos? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log_info "Limpiando contenedores..."
        docker-compose down -v 2>/dev/null || true
        docker-compose -f docker-compose.prod.yml down -v 2>/dev/null || true
        
        log_info "Eliminando imagen..."
        docker rmi sistema-equipos 2>/dev/null || true
        
        log_success "Limpieza completada"
    else
        log_info "Limpieza cancelada"
    fi
}

# Menú principal
show_menu() {
    echo ""
    echo "=================================="
    echo "   Sistema de Préstamos - Deploy   "
    echo "=================================="
    echo "1. Desplegar en desarrollo"
    echo "2. Desplegar en producción"
    echo "3. Mostrar estado"
    echo "4. Crear backup"
    echo "5. Limpiar deployment"
    echo "6. Salir"
    echo "=================================="
}

# Función principal
main() {
    log_info "Sistema de Préstamos de Equipos - Script de Despliegue"
    
    # Verificaciones previas
    check_docker
    check_files
    setup_data_dir
    
    # Si se pasa argumento, ejecutar directamente
    if [[ $# -gt 0 ]]; then
        case $1 in
            "desarrollo"|"dev")
                deploy_development
                ;;
            "produccion"|"prod")
                deploy_production
                ;;
            "status")
                show_status
                ;;
            "backup")
                create_backup
                ;;
            "clean")
                cleanup
                ;;
            *)
                log_error "Argumento no válido. Usa: desarrollo, produccion, status, backup, clean"
                exit 1
                ;;
        esac
        exit 0
    fi
    
    # Menú interactivo
    while true; do
        show_menu
        read -p "Selecciona una opción (1-6): " choice
        
        case $choice in
            1)
                deploy_development
                ;;
            2)
                deploy_production
                ;;
            3)
                show_status
                ;;
            4)
                create_backup
                ;;
            5)
                cleanup
                ;;
            6)
                log_info "¡Hasta luego!"
                exit 0
                ;;
            *)
                log_error "Opción no válida"
                ;;
        esac
        
        echo ""
        read -p "Presiona Enter para continuar..."
    done
}

# Ejecutar función principal con todos los argumentos
main "$@"