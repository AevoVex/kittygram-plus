# Kittygram Plus

Проект состоит из Django REST API, React SPA и Nginx-шлюза.

```text
kittygram/
├── backend/                  # Django, DRF, Gunicorn
├── frontend/                 # React SPA
├── gateway/                  # Nginx
├── docker-compose.yml        # локальная сборка
└── docker-compose.production.yml
```

## Локальный запуск

```bash
cp .env.example .env
docker compose up -d --build
```

Приложение открывается на `http://localhost:8080/`. Backend не публикует порт наружу: запросы `/api/`, `/auth/` и `/admin/` проксируются через gateway.

Статика backend и frontend складывается в общий volume `static_value`, медиа — в `media_value`.

## API-документация и проверка

- [Контракт API совместных подборок](docs/API_COLLABORATIVE_COLLECTIONS.md)
- Swagger UI: [`/api/docs/`](http://localhost:8080/api/docs/); OpenAPI-схема: [`/api/schema/`](http://localhost:8080/api/schema/)
- [Postman-коллекция](postman/Kittygram%20Collaborative%20Collections.postman_collection.json)
- [Полный Postman-прогон всех вариантов](postman/Kittygram%20Full%20API%20Run.postman_collection.json)
- [Инструкция по Docker и локальной проверке](docs/DOCKER_VERIFICATION.md)
- [Демо-данные для быстрого тестирования](docs/DEMO_DATA.md)
- [Черновик курсовой работы](docs/COURSEWORK_COLLABORATIVE_COLLECTIONS.md)
- [Use Case и Deployment-диаграммы](docs/diagrams/)
- [Скриншоты доказательств](docs/evidence/README.md)

## Production

В `.env` на сервере укажите реальные значения:

```env
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=long-random-secret
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,89.125.39.139
POSTGRES_DB=kittygram
POSTGRES_USER=kittygram
POSTGRES_PASSWORD=strong-password
DOCKER_USERNAME=your-dockerhub-username
```

Production compose использует готовые образы из Docker Hub:

```bash
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d
```

`backend` сам последовательно выполняет миграции и `collectstatic` в entrypoint;
не запускайте эти команды параллельно через `docker compose exec`.

## CI/CD

Workflow находится в [`.github/workflows/main.yml`](../.github/workflows/main.yml). Он запускает PostgreSQL, backend-тесты, React build, сборку и публикацию трёх образов:

- `kittygram_plus_backend`
- `kittygram_plus_frontend`
- `kittygram_plus_gateway`

После публикации workflow может выполнить деплой по SSH. Для этого в GitHub Secrets нужны `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `HOST`, `USER`, `SSH_KEY`, `SSH_PASSPHRASE`. На сервере репозиторий находится в `~/kittygram-plus`.

CI check
