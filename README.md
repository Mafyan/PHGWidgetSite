## Что это

**Безопасный прокси‑сервис** для получения расписания из **1C Fitness (cloud.1c.fitness)** по API и отдачи данных на сайт/виджет **без передачи логина/пароля** в браузер.

## Почему это безопасно

- **Basic логин/пароль + API Key хранятся только на сервере** (env / `.env`), фронту они не выдаются.
- **CORS whitelist**: можно разрешить запросы только с ваших доменов.
- **Rate limit** на IP (простая защита от злоупотреблений).
- **Кэш** на короткое время (меньше нагрузка на 1C).

## Быстрый старт (Windows)

1) Установите Python 3.11+  
2) В корне проекта:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

3) Создайте файл `.env` рядом с `requirements.txt` (можно скопировать из `env.example`) и заполните:

- `ONEC_BASE_URL`
- `ONEC_BASIC_USER`
- `ONEC_BASIC_PASS`
- `ONEC_API_KEY`
- `CORS_ALLOW_ORIGINS` (ваши домены)

4) Запуск:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Проверка:
- `GET /health`
- `GET /widget` (демо‑страница)

## API для виджета

### Получить расписание групповых занятий за период

`GET /api/classes?start_date=YYYY-MM-DD%20HH:MM&end_date=YYYY-MM-DD%20HH:MM`

Ответ: **массив объектов**, нормализованный под виджет (минимально нужные поля).

## Встраивание виджета на сайт

1) Положите файл `widget/schedule-widget.js` на ваш сайт/хостинг (или отдавайте как static).  
2) Добавьте контейнер:

```html
<div
  data-onec-schedule
  data-api-base="https://YOUR-PROXY-DOMAIN"
  data-start-date="2025-01-01 00:00"
  data-end-date="2025-01-07 23:59"
></div>
<script src="/path/to/schedule-widget.js"></script>
```

## Важно про параметры 1C

Метод `{classes}` в разных установках 1C может ожидать query‑параметры с разными именами.  
Сейчас прокси шлет: `start_date`, `end_date` (и опционально `club_id`). Если ваш сервер 1C ожидает другие ключи — скажите, я подстрою.

