# Docker: локальный запуск и проверка

## Переменные окружения

Создайте `.env` только из `.env.example` и укажите собственные значения:

```powershell
Copy-Item .env.example .env
```

Не добавляйте `.env` в репозиторий. Файл уже исключён `.gitignore`.

## Локальный запуск

```powershell
docker compose up -d --build
docker compose ps
docker compose logs backend --tail 100
```

Backend-контейнер сам выполнит `migrate` и `collectstatic` перед запуском
Gunicorn. После запуска приложение должно быть доступно по
`http://localhost:8080/`.

## Проверка конфигурации без `.env`

Compose принимает переменную `ENV_FILE`; по умолчанию она равна `.env`. Для
проверки схемы без создания локального файла:

```powershell
$env:ENV_FILE = '.env.example'
docker compose config --quiet
Remove-Item Env:ENV_FILE
```

Эта команда проверяет итоговую Compose-конфигурацию, но не запускает контейнеры
и не подтверждает работоспособность PostgreSQL, Nginx или API.

## Результат локальной проверки

Проверка выполнена 28.10.2026 с отдельным временным именем Compose-проекта и
примерными значениями из `.env.example`:

- `docker compose config --quiet` выполнен успешно;
- образы backend, frontend и gateway собраны успешно;
- PostgreSQL прошёл healthcheck, backend применил миграции;
- `GET /api/collections/` через Nginx вернул ожидаемый `401` без JWT;
- `showmigrations collaborations` подтвердил миграции `0001_initial` и
  `0002_collectioncatproposal`;
- после проверки временные контейнеры, сеть и volumes были удалены.

Контейнер `frontend` намеренно завершает работу с кодом `0`: он копирует
собранную статику в общий volume. Поэтому не используйте `docker compose up
--wait` как единственный критерий работоспособности этого Compose-проекта.

Проверка не является подтверждением внешнего деплоя, работы реального домена,
HTTPS или production-секретов.

## Проверка после запуска

```powershell
Invoke-WebRequest http://localhost:8080/api/collections/ -Method GET
docker compose exec backend python manage.py showmigrations collaborations
docker compose exec backend python manage.py test cats collaborations
```

Первый запрос без JWT должен вернуть `401`, что подтверждает доступность Nginx
и backend. Второй подтверждает применение миграций `0001` и `0002`. Для
проверки сценариев с ролями и заявками используйте Postman-коллекцию.

## Очистка локальных контейнеров

```powershell
docker compose down
```

Эта команда останавливает и удаляет контейнеры, но сохраняет именованные
volumes. Удаление volumes с данными PostgreSQL выполняйте только осознанно.
