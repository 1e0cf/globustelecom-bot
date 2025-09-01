# Project Overview

This project is a template for creating a scalable Telegram bot with integrated analytics and admin capabilities. It's built using Python with a strong focus on asynchronous operations and modern development practices.

Key features include:
- Telegram bot powered by `aiogram`.
- Admin panel using `Flask-Admin` with `AdminLTE` theme.
- Database interactions via `SQLAlchemy` with migrations handled by `Alembic`.
- Caching with `Redis`.
- Analytics integration (Amplitude, PostHog, Google Analytics).
- Performance monitoring with `Prometheus` and `Grafana`.
- Error tracking with `Sentry`.
- Internationalization (i18n) support using `Babel`.
- Containerization with `Docker` and orchestration via `Docker Compose`.
- Dependency management and virtual environment handling with `uv`.
- Code quality ensured by `ruff` (linting and formatting) and `mypy` (type checking).
- CI/CD pipelines configured.

The project is structured into two main parts: the `bot` directory for the Telegram bot logic and the `admin` directory for the Flask-based admin panel.

# Building and Running

## Prerequisites
- Python 3.10+
- `uv` package manager (https://docs.astral.sh/uv/)
- Docker and Docker Compose (for containerized deployment)

## Local Development

1.  **Install Dependencies:**
    Use `uv` to create a virtual environment and install all dependencies as defined in `pyproject.toml`.
    ```bash
    uv sync --frozen --all-groups
    ```
2.  **Set up Environment Variables:**
    Copy `.env.example` to `.env` and configure the necessary environment variables, especially `BOT_TOKEN`, `DB_*`, and `REDIS_*`.
3.  **Ensure Services are Running:**
    You need a running PostgreSQL database and a Redis instance. These can be started locally or via Docker (see Docker section).
4.  **Run the Bot:**
    ```bash
    uv run python -m bot
    ```
5.  **Run the Admin Panel:**
    ```bash
    uv run gunicorn -c admin/gunicorn_conf.py
    ```
6.  **Run Database Migrations:**
    ```bash
    uv run alembic upgrade head
    ```

## Docker (Recommended for Deployment)

1.  **Configure Environment Variables:**
    Ensure `.env` is correctly set up.
2.  **Build and Start Services:**
    This command builds the necessary images and starts all services defined in `docker-compose.yml` (bot, admin, postgres, redis, pgbouncer, prometheus, grafana, etc.).
    ```bash
    docker compose up -d --build
    ```

## Useful Makefile Commands

The `Makefile` provides shortcuts for common tasks:
- `make deps`: Install dependencies using `uv`.
- `make compose-up`: Run `docker compose up --build -d`.
- `make compose-down`: Run `docker compose down`.
- `make check`: Run code linters (`ruff check` and `ruff format --check`).
- `make format`: Run code formatters (`ruff check --fix` and `ruff format`).
- `make migrate`: Run `alembic upgrade head` within the bot container.
- `make mm args="migration_name"`: Create a new Alembic migration.
- `make babel-extract`: Extract translatable strings.
- `make babel-compile`: Compile translation files.

# Development Conventions

- **Dependency Management:** Uses `uv` with `pyproject.toml` and `uv.lock` for fast, reliable dependency resolution and environment setup.
- **Code Style:** Enforced using `ruff`. Configuration is in `pyproject.toml`. Run `make check` or `make format`.
- **Type Checking:** Performed by `mypy`. Configuration is in `pyproject.toml`.
- **Pre-commit Hooks:** Configured via `.pre-commit-config.yaml` to automatically check/format code on commit.
- **Database Migrations:** Managed by `Alembic`. New migrations should be created using `alembic revision --autogenerate -m "message"` and applied with `alembic upgrade head`.
- **Internationalization:** Uses `Babel` for managing translations. Strings are extracted to `.pot` files and compiled from `.po` to `.mo` files.
- **Logging:** Uses `loguru` for structured logging.
- **Configuration:** Settings are managed using `pydantic-settings` in `bot/core/config.py`, loaded from environment variables (`.env` file).
- **Structure:**
  - `bot/`: Contains all Telegram bot related code.
    - `handlers/`: Logic for processing user commands/messages.
    - `services/`: Core business logic.
    - `keyboards/`: Definitions for Telegram keyboards.
    - `middlewares/`: Interceptors for processing updates.
    - `database/`: SQLAlchemy models and database interaction logic.
    - `cache/`: Redis caching logic.
    - `analytics/`: Integration with analytics services.
    - `core/`: Configuration and application setup.
    - `utils/`: Helper functions.
    - `locales/`: Translation files.
  - `admin/`: Contains all Flask admin panel related code.
    - `views/`: Custom views for Flask-Admin.
    - `templates/`: HTML templates.
    - `static/`: Static assets (CSS, JS, images).
    - `app.py`: Main Flask application setup.
    - `config.py`: Flask application configuration.
  - `migrations/`: Alembic migration scripts.
  - `configs/`: Configuration files for monitoring tools (Prometheus, Grafana).