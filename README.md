# Остаточные знания — Московский Политех

Учебный проект «Автоматизация внутренних бизнес-процессов университета».
Ветка содержит базовый FastAPI-каркас, конфигурацию, ошибки, логирование,
асинхронный слой SQLAlchemy/MySQL и предварительные ORM-модели.
Это не готовая бизнес-система. Исходный Flask-проект, включая старые конфигурации
развёртывания, сохранён в legacy/flask и не импортируется новым приложением.

## Architecture

Router → Service → SQLAlchemy / AsyncSession → MySQL

Модульный монолит: одно приложение и общая база; каждый модуль владеет своими
данными. ORM-модели находятся в app/modules/<module>/models.py.
Связи заданы строковыми ForeignKey без циклических импортов ORM-классов.
Публичные сервисы, бизнес-endpoint'ы и Pydantic-контракты доменных модулей
в этой ветке ещё не реализованы. Общий API router подготовлен, но пока пуст.

Settings читает environment и .env. get_db_session создаёт отдельную AsyncSession
на запрос и закрывает её; при закрытии незавершённая транзакция откатывается.
Приложение регистрирует metadata девяти моделей, но не создаёт таблицы при старте.

ApplicationError преобразуется общим handler в JSON с полем detail:
400 — общая ошибка, 404 — объект не найден, 409 — конфликт, 403 — запрещено,
422 — нарушение бизнес-правила, 501 — операция ещё не реализована.
Входные данные проверяет FastAPI. Неожиданные ошибки обрабатываются сервером.
Стандартный logging выводит время, уровень, имя logger и сообщение в консоль;
уровень задаётся LOG_LEVEL. Записи бизнес-событий пока не добавлены.

## Требования и локальный запуск

Python 3.12+, MySQL 8.4. Для контейнерного запуска нужен Docker Compose.
PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Замените примерные пароли. Для локального backend поменяйте хост db на localhost
в DATABASE_URL. Логин, пароль и база должны совпадать с MYSQL_*.
Специальные символы в пароле URL нужно кодировать. .env не хранится в Git.

```powershell
docker compose up -d db
.venv\Scripts\python -m uvicorn app.main:app --reload
```

## Docker

В .env для контейнерного backend оставьте хост db.

```powershell
docker compose up --build -d
docker compose logs backend
```

Backend: http://localhost:8000. MySQL хранит данные в постоянном volume.
MYSQL_* применяется при первой инициализации базы.
Healthcheck проверяет доступность процесса backend, а не наличие таблиц.

## Swagger

- Swagger: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json
- Health: http://localhost:8000/health

GET /health возвращает {"status": "ok"} и не требует подключения к БД.
В Swagger сейчас только health: бизнес-маршруты будут добавляться отдельно.

## Проверки

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
```

Тесты проверяют application, health, Swagger, Settings, обработчики ошибок,
жизненный цикл сессии и сборку metadata/DDL моделей. MySQL для них не требуется;
они не проверяют реальное выполнение SQL-запросов в MySQL.

## Что будет добавлено отдельно

Alembic и начальная миграция, domain schemas/routers/services, авторизация,
интеграции, dashboard, сохранение результатов и workflow отчётов.
Таблицы сейчас не создаются автоматически. До добавления миграций не подключайте
каркас к рабочей legacy-базе: схемы различаются и нужен отдельный план переноса.

## Структура

```text
app/
  main.py
  core/
  api/
  db/
  modules/
    users/
    departments/
    periods/
    groups/
    disciplines/
    students/
    testing/
    results/
    reports/
tests/
legacy/flask/
```
