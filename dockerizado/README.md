# Sistema de Préstamos de Equipos - Docker

Un sistema web desarrollado con Streamlit para gestionar préstamos de equipos tecnológicos con códigos QR para acceso rápido.

## 🚀 Características

- **Gestión de equipos**: Registro y administración de inventario
- **Préstamos y devoluciones**: Control de transacciones
- **Códigos QR**: Acceso rápido mediante escaneo
- **Reportes**: Estadísticas y historial de transacciones
- **Base de datos SQLite**: Almacenamiento local persistente

## 📋 Requisitos Previos

- Docker
- Docker Compose

## 🐳 Despliegue con Docker

### Opción 1: Despliegue rápido

```bash
# Clonar el repositorio (o descargar archivos)
git clone <tu-repo>
cd sistema-equipos

# Construir y ejecutar
docker-compose up -d
```

### Opción 2: Construcción paso a paso

```bash
# Construir la imagen
docker build -t sistema-equipos .

# Ejecutar el contenedor
docker run -d \
  --name sistema-equipos \
  -p 8501:8501 \
  -v $(pwd)/equipos.db:/app/equipos.db \
  -e BASE_URL=http://localhost:8501 \
  sistema-equipos
```

## 🔧 Configuración

### Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `BASE_URL` | URL base para APP | `http://localhost:8501` |
| `DB_PATH` | Ruta de la base de datos | `equipos.db` |

### Para Producción

1. **Modificar BASE_URL**: Cambiar en `docker-compose.yml`
   ```yaml
   environment:
     - BASE_URL=https://tu-dominio.com
   ```

2. **Usar proxy reverso** (Nginx/Apache):
   ```nginx
   server {
       listen 80;
       server_name tu-dominio.com;
       
       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **SSL con Let's Encrypt**:
   ```bash
   certbot --nginx -d tu-dominio.com
   ```

## 📂 Estructura de Archivos

```
.
├── app.py                 # Aplicación principal
├── requirements.txt       # Dependencias Python
├── Dockerfile            # Configuración Docker
├── docker-compose.yml    # Orquestación de servicios
├── .dockerignore        # Archivos excluidos del build
├── equipos.db           # Base de datos SQLite (se crea automáticamente)
└── README.md            # Este archivo
```

## 💾 Respaldo de Datos

### Crear respaldo
```bash
# Copiar base de datos del contenedor
docker cp sistema-equipos:/app/equipos.db ./backup-$(date +%Y%m%d).db
```

### Restaurar respaldo
```bash
# Detener contenedor
docker-compose down

# Restaurar archivo
cp backup-20240101.db equipos.db

# Reiniciar
docker-compose up -d
```

## 🔍 Monitoreo y Logs

```bash
# Ver logs en tiempo real
docker-compose logs -f

# Ver estado de servicios
docker-compose ps

# Verificar salud del contenedor
docker inspect sistema-equipos --format='{{.State.Health.Status}}'
```

## 🛠️ Comandos Útiles

```bash
# Reconstruir imagen
docker-compose build --no-cache

# Reiniciar servicios
docker-compose restart

# Acceder al contenedor
docker exec -it sistema-equipos /bin/bash

# Limpiar todo (¡CUIDADO! Elimina datos)
docker-compose down -v
docker rmi sistema-equipos
```

## 📱 Acceso

Una vez desplegado, accede a la aplicación en:
- **Local**: http://localhost:8501
- **Producción**: https://tu-dominio.com

## 🐛 Solución de Problemas

### Puerto ocupado
```bash
# Verificar qué usa el puerto 8501
sudo lsof -i :8501

# Cambiar puerto en docker-compose.yml
ports:
  - "8502:8501"  # Usar puerto 8502 externamente
```

### Problemas de permisos
```bash
# Arreglar permisos de la base de datos
sudo chown $USER:$USER equipos.db
```

### Imagen no construye
```bash
# Limpiar cache de Docker
docker system prune -a
docker-compose build --no-cache
```

## 🔐 Seguridad

- La aplicación usa un usuario no-root dentro del contenedor
- La base de datos está limitada al contenedor
- No se exponen puertos adicionales innecesarios

## 📝 Notas de Desarrollo

- La base de datos SQLite se crea automáticamente al primer inicio
- Los códigos QR se generan dinámicamente
- La aplicación es stateless excepto por la base de datos
- Compatible con ARM64 y AMD64

## 🤝 Contribuir

1. Fork del proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request