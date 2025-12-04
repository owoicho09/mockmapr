# Core - Django REST API

A production-ready Django REST API project.

## Features

- ✅ Django REST Framework
- ✅ CORS Headers Support
- ✅ Jazzmin Admin Interface
- ✅ Environment Variables Support
- ✅ PostgreSQL Ready
- ✅ WhiteNoise Static Files
- ✅ Gunicorn Production Server
- ✅ Security Best Practices

## Setup

1. **Activate Virtual Environment:**
   ```bash
   # Windows
   venv\Scripts\activate

   # Mac/Linux
   source venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   - Copy `.env.example` to `.env`
   - Update environment variables as needed

4. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create Superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run Development Server:**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

- `http://localhost:8000/api/health/` - Health check
- `http://localhost:8000/api/ping/` - Ping test
- `http://localhost:8000/api/items/` - Items CRUD
- `http://localhost:8000/admin/` - Admin interface

## Production Deployment

1. **Set Environment Variables:**
   ```bash
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com
   DATABASE_URL=postgresql://user:pass@host:port/db
   ```

2. **Collect Static Files:**
   ```bash
   python manage.py collectstatic
   ```

3. **Run with Gunicorn:**
   ```bash
   gunicorn core.wsgi:application
   ```

## Project Structure

```
core/
├── mockmap/          # Main application
├── core/    # Project settings
├── venv/            # Virtual environment
├── .env             # Environment variables
├── requirements.txt # Dependencies
└── manage.py        # Django management script
```

## License

MIT
