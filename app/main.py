from __future__ import annotations

import logging
from typing import Any

from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.onecf_client import UpstreamError, get_classes
from app.security import SlidingWindowRateLimiter
from app.settings import settings


logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("cooking-proxy")

app = FastAPI(title="1C Fitness Proxy", version="1.0.0")

# CORS: разрешаем только явно указанные домены (иначе — никого).
origins = settings.cors_origins_list()
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
        max_age=600,
    )

rate_limiter = SlidingWindowRateLimiter(
    limit=settings.rate_limit_requests, window_seconds=settings.rate_limit_window_seconds
)

# Кэшируем по (start_date, end_date, club_id)
classes_cache: TTLCache[tuple[str, str, str], list[dict[str, Any]]] = TTLCache(
    maxsize=256, ttl=settings.cache_ttl_seconds
)


def _client_ip(request: Request) -> str:
    # Если будет reverse-proxy, лучше настроить доверенный X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _sanitize_class(item: dict[str, Any]) -> dict[str, Any]:
    """
    Отдаем только то, что нужно виджету. Так мы уменьшаем объем данных и
    снижаем риск утечки персональных данных/внутренних полей.
    """
    service = item.get("service") or {}
    room = item.get("room") or {}
    employee = item.get("employee") or {}

    return {
        "appointment_id": item.get("appointment_id"),
        "title": service.get("title") or item.get("title"),
        "service_id": service.get("id"),
        "start_date": item.get("start_date"),
        "end_date": item.get("end_date"),
        "duration": item.get("duration"),
        "capacity": item.get("capacity"),
        "booked": item.get("booked"),
        "web_booked": item.get("web_booked"),
        "web_capacity": item.get("web_capacity"),
        "online": item.get("online"),
        "canceled": item.get("canceled"),
        "reason_for_cancellation": item.get("reason_for_cancellation"),
        "room": {"id": room.get("id"), "title": room.get("title")},
        "employee": {"id": employee.get("id"), "name": employee.get("name")},
        "color": (service.get("color") if isinstance(service, dict) else None),
    }


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/classes")
async def api_classes(
    request: Request,
    start_date: str,
    end_date: str,
    club_id: str | None = None,
) -> JSONResponse:
    rl = rate_limiter.check(_client_ip(request))
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": str(rl.reset_seconds)},
        )

    cache_key = (start_date, end_date, club_id or "")
    if cache_key in classes_cache:
        payload = classes_cache[cache_key]
        return JSONResponse(
            payload,
            headers={
                "Cache-Control": "no-store",
                "X-Cache": "HIT",
                "X-RateLimit-Remaining": str(rl.remaining),
            },
        )

    try:
        raw = await get_classes(start_date=start_date, end_date=end_date, club_id=club_id)
    except UpstreamError as e:
        logger.exception("Failed to fetch classes from 1C")
        if settings.debug_upstream_errors:
            detail = {
                "message": "Upstream 1C Fitness error",
                "status_code": e.status_code,
                "url": e.url,
                "body": e.body,
            }
        else:
            detail = "Upstream 1C Fitness error"
        raise HTTPException(status_code=502, detail=detail) from e
    except Exception as e:
        logger.exception("Failed to fetch classes from 1C (unexpected)")
        raise HTTPException(status_code=502, detail="Upstream 1C Fitness error") from e

    sanitized = [_sanitize_class(x) for x in raw if isinstance(x, dict)]
    classes_cache[cache_key] = sanitized
    return JSONResponse(
        sanitized,
        headers={
            "Cache-Control": "no-store",
            "X-Cache": "MISS",
            "X-RateLimit-Remaining": str(rl.remaining),
        },
    )


@app.get("/widget", response_class=HTMLResponse)
async def widget_demo() -> str:
    # Мини-демо страница (удобно проверять без интеграции на сайт).
    return """<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Schedule Widget Demo</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
      .wrap { max-width: 920px; }
      .row { display: flex; gap: 12px; flex-wrap: wrap; align-items: end; }
      label { display:block; font-size: 12px; opacity: .8; margin-bottom: 6px; }
      input { padding: 8px 10px; border: 1px solid #ddd; border-radius: 8px; }
      button { padding: 9px 12px; border: 0; border-radius: 10px; background: #111; color: #fff; cursor: pointer;}
      pre { background: #0b1020; color: #e5e7eb; padding: 12px; border-radius: 12px; overflow:auto; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <h2>Виджет расписания (демо)</h2>
      <div class="row">
        <div>
          <label>start_date (yyyy-mm-dd HH:MM)</label>
          <input id="s" value="2025-01-01 00:00" />
        </div>
        <div>
          <label>end_date (yyyy-mm-dd HH:MM)</label>
          <input id="e" value="2025-01-07 23:59" />
        </div>
        <button id="btn">Загрузить</button>
      </div>
      <div style="height:12px"></div>
      <pre id="out">Нажмите “Загрузить”</pre>
    </div>
    <script>
      const out = document.getElementById('out');
      document.getElementById('btn').addEventListener('click', async () => {
        out.textContent = 'Загрузка...';
        const start = document.getElementById('s').value;
        const end = document.getElementById('e').value;
        const url = `/api/classes?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`;
        const r = await fetch(url, { headers: { 'Accept': 'application/json' }});
        const txt = await r.text();
        out.textContent = txt;
      });
    </script>
  </body>
</html>"""


