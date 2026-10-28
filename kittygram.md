# Полное руководство по проекту Kittygram (KittyBot, DRF, Docker, Деплой, CI/CD)

---

## ЧАСТЬ 1. Telegram-бот KittyBot

### 1. Регистрация и настройка бота
1. Откройте Telegram, найдите бота `@BotFather` (с синей галочкой) и нажмите `/start`.
2. Отправьте команду `/newbot`.
3. Укажите:
   - Отображаемое имя (например, `MyKittyBot`).
   - Технический юзернейм, оканчивающийся на `bot` (например, `my_super_kitty_bot`).
4. Скопируйте полученный API-токен: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`.
5. Узнайте свой `Chat ID` через бота `@userinfobot`.

---

### 2. Подготовка локального окружения
```bash
mkdir kittybot && cd kittybot
python -m venv venv

# Активация окружения:
# Linux/macOS:
source venv/bin/activate
# Windows:
source venv/Scripts/activate

pip install pyTelegramBotAPI==4.14.1 requests python-dotenv==1.0.1
```

Создайте файл `.env`:
```env
TELEGRAM_TOKEN=ваш_токен_от_BotFather
```

Создайте `.gitignore`:
```gitignore
venv/
.env
__pycache__/
*.log
```

---

### 3. Реализация логики бота с логированием и обработкой исключений
Создайте файл `kittybot.py`:

```python
import logging
import os
import requests
from dotenv import load_dotenv
from telebot import TeleBot, types

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('main.log', mode='a', encoding='utf-8')
    ]
)

bot = TeleBot(token=TELEGRAM_TOKEN)

URL_CAT = 'https://api.thecatapi.com/v1/images/search'
URL_DOG = 'https://api.thedogapi.com/v1/images/search'


def get_new_image():
    """Получение случайной картинки котика или собаки в случае сбоя."""
    try:
        response = requests.get(URL_CAT)
        response.raise_for_status()
        data = response.json()
        return data[0].get('url')
    except Exception as error:
        logging.error(f'Ошибка при запросе к Cat API: {error}. Переключаемся на Dog API.')
        try:
            response = requests.get(URL_DOG)
            response.raise_for_status()
            return response.json()[0].get('url')
        except Exception as dog_error:
            logging.critical(f'Оба API недоступны: {dog_error}')
            return None


@bot.message_handler(commands=['start'])
def wake_up(message):
    chat_id = message.chat.id
    name = message.from_user.first_name

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_newcat = types.KeyboardButton('/newcat')
    keyboard.add(button_newcat)

    bot.send_message(
        chat_id=chat_id,
        text=f'Привет, {name}! Посмотри, какого котика я тебе нашел 🐱',
        reply_markup=keyboard,
    )
    image_url = get_new_image()
    if image_url:
        bot.send_photo(chat_id, image_url)
    else:
        bot.send_message(chat_id, 'Котики временно спят!')


@bot.message_handler(commands=['newcat'])
def new_cat(message):
    chat_id = message.chat.id
    image_url = get_new_image()
    if image_url:
        bot.send_photo(chat_id, image_url)
    else:
        bot.send_message(chat_id, 'Не удалось загрузить изображение котика.')


@bot.message_handler(content_types=['text'])
def say_hi(message):
    bot.send_message(message.chat.id, 'Привет, я KittyBot! Нажми /newcat для фото котика.')


def main():
    logging.info('Бот запущен')
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
```

Запуск:
```bash
python kittybot.py
```

---

## ЧАСТЬ 2. Разработка бэкенда Kittygram на Django REST Framework

### 1. Архитектура моделей (`cats/models.py`)
```python
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Achievement(models.Model):
    name = models.CharField(max_length=64, verbose_name='Достижение')

    def __str__(self):
        return self.name


class Cat(models.Model):
    name = models.CharField(max_length=16, verbose_name='Имя')
    color = models.CharField(max_length=16, verbose_name='Цвет')
    birth_year = models.IntegerField(verbose_name='Год рождения')
    owner = models.ForeignKey(
        User,
        related_name='cats',
        on_delete=models.CASCADE,
        verbose_name='Хозяин'
    )
    achievements = models.ManyToManyField(
        Achievement,
        through='AchievementCat',
        verbose_name='Достижения'
    )
    image = models.ImageField(
        upload_to='cats/images/',
        null=True,
        default=None,
        verbose_name='Изображение'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'owner'],
                name='unique_cat_per_owner'
            )
        ]

    def __str__(self):
        return self.name


class AchievementCat(models.Model):
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    cat = models.ForeignKey(Cat, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.cat} -> {self.achievement}'
```

---

### 2. Пользовательские поля и сериализаторы (`cats/serializers.py`)
```python
import base64
import datetime as dt
import webcolors
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import Achievement, AchievementCat, Cat, User


class Hex2NameColor(serializers.Field):
    """Кастомное поле преобразования HEX-кода в именованный цвет."""
    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        try:
            return webcolors.hex_to_name(data)
        except ValueError:
            raise serializers.ValidationError('Для этого цвета нет стандартного имени')


class Base64ImageField(serializers.ImageField):
    """Кастомное поле для декодирования картинок из base64 строки."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format_str, imgstr = data.split(';base64,')
            ext = format_str.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class AchievementSerializer(serializers.ModelSerializer):
    achievement_name = serializers.CharField(source='name')

    class Meta:
        model = Achievement
        fields = ('id', 'achievement_name')


class CatSerializer(serializers.ModelSerializer):
    achievements = AchievementSerializer(many=True, required=False)
    color = Hex2NameColor()
    age = serializers.SerializerMethodField()
    owner = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Cat
        fields = (
            'id', 'name', 'color', 'birth_year', 'achievements',
            'owner', 'age', 'image'
        )
        read_only_fields = ('owner',)
        validators = [
            UniqueTogetherValidator(
                queryset=Cat.objects.all(),
                fields=('name', 'owner'),
                message='У вас уже есть котик с таким именем!'
            )
        ]

    def get_age(self, obj):
        return dt.datetime.now().year - obj.birth_year

    def validate_birth_year(self, value):
        current_year = dt.date.today().year
        if not (current_year - 40 < value <= current_year):
            raise serializers.ValidationError('Проверьте год рождения котика!')
        return value

    def validate(self, data):
        if data.get('color') == data.get('name'):
            raise serializers.ValidationError('Имя котика не может совпадать с его цветом!')
        return data

    def create(self, validated_data):
        if 'achievements' not in self.initial_data:
            return Cat.objects.create(**validated_data)

        achievements_data = validated_data.pop('achievements')
        cat = Cat.objects.create(**validated_data)
        for achievement in achievements_data:
            current_achievement, _ = Achievement.objects.get_or_create(**achievement)
            AchievementCat.objects.create(achievement=current_achievement, cat=cat)
        return cat

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.color = validated_data.get('color', instance.color)
        instance.birth_year = validated_data.get('birth_year', instance.birth_year)
        instance.image = validated_data.get('image', instance.image)

        if 'achievements' in validated_data:
            achievements_data = validated_data.pop('achievements')
            lst = []
            for item in achievements_data:
                current_achievement, _ = Achievement.objects.get_or_create(**item)
                lst.append(current_achievement)
            instance.achievements.set(lst)

        instance.save()
        return instance


class CatListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cat
        fields = ('id', 'name', 'color')


class UserSerializer(serializers.ModelSerializer):
    cats = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'cats')
```

---

### 3. Разграничение прав и ограничения (`cats/permissions.py`, `cats/throttling.py`)

`cats/permissions.py`:
```python
from rest_framework import permissions


class OwnerOrReadOnly(permissions.BasePermission):
    """Чтение доступно всем, модификация — только автору."""
    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class ReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
```

`cats/throttling.py`:
```python
import datetime
from rest_framework import throttling


class WorkingHoursRateThrottle(throttling.BaseThrottle):
    """Пример кастомного троттлинга для отключения запросов в ночные часы."""
    def allow_request(self, request, view):
        now = datetime.datetime.now().hour
        if 3 <= now < 5:
            return False
        return True
```

---

### 4. Контроллеры (`cats/views.py`)
```python
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Achievement, Cat, User
from .permissions import OwnerOrReadOnly, ReadOnly
from .serializers import (
    AchievementSerializer,
    CatListSerializer,
    CatSerializer,
    UserSerializer,
)


class CatViewSet(viewsets.ModelViewSet):
    queryset = Cat.objects.all()
    serializer_class = CatSerializer
    permission_classes = (OwnerOrReadOnly,)
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    )
    filterset_fields = ('color', 'birth_year')
    search_fields = ('name', 'achievements__name', 'owner__username')
    ordering_fields = ('name', 'birth_year')
    ordering = ('birth_year',)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return CatListSerializer
        return CatSerializer

    def get_permissions(self):
        if self.action == 'retrieve':
            return (ReadOnly(),)
        return super().get_permissions()

    @action(detail=False, url_path='recent-white-cats')
    def recent_white_cats(self, request):
        """Кастомный эндпоинт для вывода последних 5 белых котов."""
        cats = Cat.objects.filter(color='white')[:5]
        serializer = self.get_serializer(cats, many=True)
        return Response(serializer.data)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class AchievementViewSet(viewsets.ModelViewSet):
    queryset = Achievement.objects.all()
    serializer_class = AchievementSerializer
```

---

### 5. Роуты и настройки проекта (`urls.py`, `settings.py`)

`kittygram/urls.py`:
```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from cats.views import AchievementViewSet, CatViewSet, UserViewSet

router = routers.DefaultRouter()
router.register(r'cats', CatViewSet)
router.register(r'users', UserViewSet)
router.register(r'achievements', AchievementViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/', include('djoser.urls')),
    path('api/', include('djoser.urls.authtoken')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

`kittygram/settings.py` (ключевые фрагменты):
```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'djoser',
    'django_filters',
    'corsheaders',
    'cats.apps.CatsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Важно: выше CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '10000/day',
        'anon': '1000/day',
    }
}

# Настройки CORS для SPA фронтенда
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_URLS_REGEX = r'^/api/.*$'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATIC_URL = '/static_backend/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static_backend')
```

---

## ЧАСТЬ 3. Контейнеризация проекта с Docker и Docker Compose

### 1. Dockerfile бэкенда (`backend/Dockerfile`)
```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN pip install --upgrade pip && pip install gunicorn==20.1.0

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "kittygram.wsgi"]
```

`.dockerignore` в `backend/`:
```dockerignore
venv/
.git/
*.sqlite3
__pycache__/
```

---

### 2. Dockerfile фронтенда (`frontend/Dockerfile`)
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build

CMD ["cp", "-r", "/app/build/.", "/frontend_static/"]
```

`.dockerignore` в `frontend/`:
```dockerignore
node_modules/
build/
```

---

### 3. Dockerfile и конфиг шлюза Nginx (`gateway/`)

`gateway/Dockerfile`:
```dockerfile
FROM nginx:1.22.1-alpine

COPY nginx.conf /etc/nginx/templates/default.conf.template
```

`gateway/nginx.conf`:
```nginx
server {
    listen 80;

    client_max_body_size 20M;

    location /api/ {
        proxy_set_header Host $http_host;
        proxy_pass http://backend:8000/api/;
    }

    location /admin/ {
        proxy_set_header Host $http_host;
        proxy_pass http://backend:8000/admin/;
    }

    location /media/ {
        alias /media/;
    }

    location / {
        alias /staticfiles/;
        index index.html;
        try_files $uri /index.html;
    }
}
```

---

### 4. Оркестрация через `docker-compose.yml`
```yaml
version: '3.8'

volumes:
  pg_data:
  static_value:
  media_value:

services:
  db:
    image: postgres:13.10-alpine
    env_file: .env
    volumes:
      - pg_data:/var/lib/postgresql/data
    restart: always

  backend:
    build: ./backend/
    env_file: .env
    volumes:
      - static_value:/backend_static
      - media_value:/app/media
    depends_on:
      - db
    restart: always

  frontend:
    build: ./frontend/
    env_file: .env
    volumes:
      - static_value:/frontend_static

  gateway:
    build: ./gateway/
    ports:
      - "80:80"
    volumes:
      - static_value:/staticfiles
      - media_value:/media
    depends_on:
      - backend
      - frontend
    restart: always
```

Создайте `.env` в корне проекта:
```env
POSTGRES_DB=kittygram
POSTGRES_USER=kittygram_user
POSTGRES_PASSWORD=kittygram_password
DB_HOST=db
DB_PORT=5432
SECRET_KEY=django-insecure-your-secret-key-here
ALLOWED_HOSTS=127.0.0.1,localhost,ваш_ip_сервера
```

---

## ЧАСТЬ 4. Развертывание (Деплой) на боевом сервере

### 1. Подготовка сервера (Ubuntu Linux)
Подключитесь по SSH:
```bash
ssh <username>@<server_ip>
```

Обновите пакеты и настройте файрвол:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install curl ufw -y

# Настройка файрвола:
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Установите Docker и Docker Compose Plugin:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install docker-compose-plugin -y
sudo usermod -aG docker $USER
```
*(Перезайдите по SSH, чтобы права группы docker применились)*.

---

### 2. Запуск контейнеров и сбор статики
1. Склонируйте репозиторий:
   ```bash
   git clone git@github.com:<ваш_логин>/kittygram.git
   cd kittygram
   ```
2. Создайте боевой файл `.env` с секретами.
3. Запустите проект:
   ```bash
   docker compose up -d --build
   ```
4. Выполните миграции и соберите статику внутри контейнеров:
   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py collectstatic --no-input
   docker compose exec backend cp -r /app/collected_static/. /backend_static/static/
   ```

---

## ЧАСТЬ 5. Автоматизация CI/CD через GitHub Actions

Создайте файл `.github/workflows/main.yml`:

```yaml
name: Kittygram Workflow

on:
  push:
    branches:
      - main

jobs:
  tests:
    name: Run Backend Tests and Linters
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13.10-alpine
        env:
          POSTGRES_USER: kittygram_user
          POSTGRES_PASSWORD: kittygram_password
          POSTGRES_DB: kittygram_test
        ports:
          - 5432:5432
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - name: Check out repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff==0.8.0
          pip install -r ./backend/requirements.txt

      - name: Run linter and tests
        env:
          POSTGRES_USER: kittygram_user
          POSTGRES_PASSWORD: kittygram_password
          POSTGRES_DB: kittygram_test
          DB_HOST: 127.0.0.1
          DB_PORT: 5432
          SECRET_KEY: test_secret_key
        run: |
          ruff check ./backend/
          cd backend/
          python manage.py test

  build_backend_and_push_to_docker_hub:
    name: Push backend to DockerHub
    runs-on: ubuntu-latest
    needs: tests
    steps:
      - name: Check out repo
        uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to DockerHub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Push to DockerHub
        uses: docker/build-push-action@v5
        with:
          context: ./backend/
          push: true
          tags: ${{ secrets.DOCKER_USERNAME }}/kittygram_backend:latest

  build_frontend_and_push_to_docker_hub:
    name: Push frontend to DockerHub
    runs-on: ubuntu-latest
    steps:
      - name: Check out repo
        uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to DockerHub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Push to DockerHub
        uses: docker/build-push-action@v5
        with:
          context: ./frontend/
          push: true
          tags: ${{ secrets.DOCKER_USERNAME }}/kittygram_frontend:latest

  build_gateway_and_push_to_docker_hub:
    name: Push gateway to DockerHub
    runs-on: ubuntu-latest
    steps:
      - name: Check out repo
        uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to DockerHub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Push to DockerHub
        uses: docker/build-push-action@v5
        with:
          context: ./gateway/
          push: true
          tags: ${{ secrets.DOCKER_USERNAME }}/kittygram_gateway:latest

  deploy:
    name: Deploy to Production Server
    runs-on: ubuntu-latest
    needs:
      - build_backend_and_push_to_docker_hub
      - build_frontend_and_push_to_docker_hub
      - build_gateway_and_push_to_docker_hub
    steps:
      - name: Executing remote ssh commands to deploy
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USER }}
          key: ${{ secrets.SSH_KEY }}
          passphrase: ${{ secrets.SSH_PASSPHRASE }}
          script: |
            cd kittygram
            docker compose pull
            docker compose down
            docker compose up -d
            docker compose exec -T backend python manage.py migrate
            docker compose exec -T backend python manage.py collectstatic --no-input
            docker compose exec -T backend cp -r /app/collected_static/. /backend_static/static/

  send_message:
    name: Send Telegram Notification
    runs-on: ubuntu-latest
    needs: deploy
    steps:
      - name: Send notification via Telegram
        uses: appleboy/telegram-action@master
        with:
          to: ${{ secrets.TELEGRAM_TO }}
          token: ${{ secrets.TELEGRAM_TOKEN }}
          message: |
            Деплой Kittygram успешно выполнен!
            Автор коммита: ${{ github.actor }}
            Сообщение: ${{ github.event.commits[0].message }}
            Ссылка на коммит: https://github.com/${{ github.repository }}/commit/${{ github.sha }}
```

### Секреты в GitHub Secrets (`Settings -> Secrets and variables -> Actions`):
- `DOCKER_USERNAME` — логин на DockerHub
- `DOCKER_PASSWORD` — токен/пароль на DockerHub
- `HOST` — внешний IP сервера
- `USER` — пользователь сервера (например, `yc-user`)
- `SSH_KEY` — приватный ключ SSH
- `SSH_PASSPHRASE` — пароль от SSH-ключа (если задан)
- `TELEGRAM_TO` — ваш Telegram Chat ID
- `TELEGRAM_TOKEN` — токен вашего Telegram-бота

---

## ЧАСТЬ 6. Чек-лист самопроверки Kittygram

### Telegram-бот KittyBot
- [ ] Токен Telegram скрыт в `.env` и не попадает в Git-репозиторий.
- [ ] Хендлеры расположены в правильном порядке: специализированные (`/start`, `/newcat`) выше общего хендлера текстовых сообщений.
- [ ] При падении Cat API бот корректно перехватывает ошибку, логирует её и присылает собаку (Dog API).
- [ ] Клавиатура с кнопкой `/newcat` использует `resize_keyboard=True`.
- [ ] Логи пишутся в файл и консоль с указанием времени, уровня и модуля.

### Django REST Framework (Бэкенд)
- [ ] Пользовательские поля: `Hex2NameColor` корректно валидирует HEX-код цвета и переводит его в читаемое название.
- [ ] Поле `image`: `Base64ImageField` принимает строки base64 и сохраняет файл в `MEDIA_ROOT`.
- [ ] Вычисляемое поле: `SerializerMethodField` возвращает возраст котика `age` на основе `birth_year`.
- [ ] Валидация: метод `validate_birth_year` отсекает котиков старше 40 лет и котиков из будущего.
- [ ] Валидация на уровне объекта: имя котика не может совпадать с его цветом.
- [ ] Вложенный сериализатор: достижения (`AchievementSerializer`) поддерживают создание и обновление через `through`-модель `AchievementCat`.
- [ ] Права доступа: редактировать и удалять котика может только его создатель (`OwnerOrReadOnly`), анонимы имеют доступ только на чтение.
- [ ] Пагинация, поиск и фильтрация: настроены `DjangoFilterBackend`, `SearchFilter` и `OrderingFilter`.

### Docker и оркестрация
- [ ] В `Dockerfile` бэкенда и фронтенда добавлены соответствующие `.dockerignore` (исключены `venv`, `node_modules`, `build`, `.git`, `db.sqlite3`).
- [ ] Для СУБД используется PostgreSQL 13+ в отдельном контейнере, данные сохраняются в именованный `volume` (`pg_data`).
- [ ] Статика бэкенда и фронтенда собирается в общий `volume` (`static_value`) и раздается Nginx из папки `/staticfiles`.
- [ ] Порт бэкенда `8000` закрыт от прямого доступа из интернета файрволом, снаружи доступен только Nginx на порту `80`.

### CI/CD (GitHub Actions)
- [ ] Ворклоу слушает push в ветку `main`.
- [ ] Этап тестирования запускает контейнер с PostgreSQL и прогоняет `ruff` и `python manage.py test`.
- [ ] Все пароли, токены и приватные ключи хранятся строго в GitHub Secrets.
- [ ] После сборки образов они успешно пушатся на DockerHub с тегом `latest`.
- [ ] По окончании деплоя на сервер приходит уведомление в Telegram.