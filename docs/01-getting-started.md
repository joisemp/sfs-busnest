# Getting Started

This guide will help you set up the SFS BusNest development environment and get the application running locally.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker Desktop** (v20.0+) - [Download](https://www.docker.com/products/docker-desktop)
- **Docker Compose** (v2.0+) - Usually included with Docker Desktop
- **Git** - [Download](https://git-scm.com/downloads)
- **Code Editor** - VS Code recommended with Python extension

### Optional Tools
- **PostgreSQL Client** (for direct database access)
- **Redis CLI** (for debugging Redis)
- **Postman** or similar (for API testing)

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/joisemp/sfs-busnest.git
cd sfs-busnest
```

### 2. Create Environment File

Create a `.env` file in the `src/config/` directory:

```bash
# Windows (PowerShell)
cd src\config
New-Item -Path .env -ItemType File

# Linux/Mac
cd src/config
touch .env
```

Add the following content to `src/config/.env`:

```env
# Environment
ENVIRONMENT=development

# Secret Key (Generate a new one for production)
SECRET_KEY=your-secret-key-here-change-in-production

# Database (Docker Compose handles this)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres

# Redis (Docker Compose handles this)
REDIS_URL=redis://redis:6379/0

# Email Backend (Console for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Debug Mode
DEBUG=True

# Allowed Hosts
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 3. Build and Start Services

```bash
# Return to project root
cd ../..

# Build Docker images
docker compose build

# Start all services
docker compose up
```

This will start:
- **app** - Django application (port 7000)
- **postgres** - PostgreSQL database (port 5432)
- **redis** - Redis cache (port 6379)
- **celery** - Background task worker
- **flower** - Celery monitoring UI (port 5555)
- **beat** - Celery periodic task scheduler

### 4. Access the Application

Once all services are running:

- **Main Application**: http://localhost:7000
- **Flower (Celery Monitor)**: http://localhost:5555
  - Username: `admin`
  - Password: `password123`

## First Time Setup

### Create Superuser

```bash
# In a new terminal, execute commands in the running container
docker exec -it sfs-busnest-container python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### Load Initial Data (Optional)

If you have fixture files:

```bash
docker exec -it sfs-busnest-container python manage.py loaddata initial_data.json
```

## Development Workflow

### Starting the Application

```bash
# Start all services
docker compose up

# Start in detached mode (background)
docker compose up -d

# View logs
docker compose logs -f app
```

### Stopping the Application

```bash
# Stop all services
docker compose down

# Stop and remove volumes (clears database)
docker compose down -v
```

### Running Management Commands

```bash
# General pattern
docker exec -it sfs-busnest-container python manage.py <command>

# Examples
docker exec -it sfs-busnest-container python manage.py makemigrations
docker exec -it sfs-busnest-container python manage.py migrate
docker exec -it sfs-busnest-container python manage.py collectstatic --noinput
docker exec -it sfs-busnest-container python manage.py shell
```

### Running Tests

```bash
# Windows (PowerShell)
cd src
$env:DJANGO_SETTINGS_MODULE="config.test_settings"
python manage.py test
$env:DJANGO_SETTINGS_MODULE="config.settings"

# Linux/Mac
cd src
DJANGO_SETTINGS_MODULE=config.test_settings python manage.py test
```

Or use the provided scripts:

```bash
# Windows
.\script\run_test.bat

# Linux/Mac
./script/run_test.sh
```

## Project Structure

```
bms-sfsinstitutions/
├── docs/                      # Documentation (you are here)
├── script/                    # Utility scripts
├── src/                       # Main application source
│   ├── config/               # Django settings and configuration
│   ├── core/                 # User authentication and profiles
│   ├── services/             # Main business logic
│   │   ├── forms/           # Django forms by role
│   │   ├── models/          # Database models (modular)
│   │   ├── views/           # Views by role
│   │   ├── urls/            # URL routing by role
│   │   └── utils/           # Utility functions
│   ├── static/              # Static files (CSS, JS, images)
│   ├── templates/           # HTML templates
│   ├── media/               # User-uploaded files
│   ├── manage.py           # Django management script
│   └── requirements.txt    # Python dependencies
├── docker-compose.yaml      # Docker services configuration
├── .gitignore
└── README.md
```

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name (development/production) | development |
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Enable debug mode | True |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | localhost |
| `DATABASE_URL` | PostgreSQL connection string | Auto-configured |
| `REDIS_URL` | Redis connection string | Auto-configured |
| `EMAIL_BACKEND` | Email backend class | console |

## Troubleshooting Setup Issues

### Docker Container Won't Start

```bash
# Check logs
docker compose logs app

# Rebuild without cache
docker compose build --no-cache

# Check Docker resources
docker system df
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker compose ps postgres

# View PostgreSQL logs
docker compose logs postgres

# Restart PostgreSQL
docker compose restart postgres
```

### Port Already in Use

```bash
# Check what's using port 7000 (Windows)
netstat -ano | findstr :7000

# Check what's using port 7000 (Linux/Mac)
lsof -i :7000

# Kill the process or change port in docker-compose.yaml
```

### Migration Errors

```bash
# Reset database (WARNING: Deletes all data)
docker compose down -v
docker compose up -d postgres
docker exec -it sfs-busnest-container python manage.py migrate
```

## Next Steps

Now that you have the application running:

1. **Explore the Application**: Log in with your superuser account
2. **Read the Architecture**: Understand [System Architecture](./03-architecture.md)
3. **Review Data Models**: Study [Data Models](./04-data-models.md)
4. **Start Developing**: Check [Backend Development](./06-backend-development.md) or [Frontend Development](./07-frontend-development.md)

## Quick Reference Commands

```bash
# Start development
docker compose up

# Create migrations
docker exec -it sfs-busnest-container python manage.py makemigrations

# Apply migrations
docker exec -it sfs-busnest-container python manage.py migrate

# Create superuser
docker exec -it sfs-busnest-container python manage.py createsuperuser

# Django shell
docker exec -it sfs-busnest-container python manage.py shell

# View logs
docker compose logs -f

# Stop services
docker compose down

# Run tests
cd src && DJANGO_SETTINGS_MODULE=config.test_settings python manage.py test
```
