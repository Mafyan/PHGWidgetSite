from __future__ import annotations

import base64
from typing import Any

import httpx

from app.settings import settings


class UpstreamError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: str | None = None,
        url: str | None = None,
        www_authenticate: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.url = url
        self.www_authenticate = www_authenticate


def _basic_auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _headers() -> dict[str, str]:
    # В документации встречается "apikey" / "apiKey". Часто ожидают именно "apikey".
    headers: dict[str, str] = {
        "Authorization": _basic_auth_header(settings.onec_basic_user, settings.onec_basic_pass),
        "apikey": settings.onec_api_key,
        "apiKey": settings.onec_api_key,
        "Accept": "application/json",
        "User-Agent": "Cooking-1CFitness-Proxy/1.0",
    }
    # Как в вашем ServerApp: добавляем варианты secret/app key, если они заданы.
    if settings.onec_secret_key:
        headers["secretkey"] = settings.onec_secret_key
        headers["secret_key"] = settings.onec_secret_key
    if settings.onec_app_key:
        headers["appkey"] = settings.onec_app_key
        headers["app_key"] = settings.onec_app_key
    return headers


def _join_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


async def get_classes(start_date: str, end_date: str, club_id: str | None = None) -> list[dict[str, Any]]:
    """
    Прокси к методу {classes}.
    Важно: параметры точного формата могут зависеть от 1C инсталляции.
    Мы передаем start_date/end_date как query.
    """
    # Как в вашем ServerApp: эндпоинт со слешем в конце.
    url = _join_url(settings.onec_base_url, "classes/")
    # На разных версиях API встречаются разные имена параметров.
    # Отправляем в двух вариантах для совместимости.
    params: list[tuple[str, str]] = [
        ("start_date", start_date),
        ("end_date", end_date),
        ("startDate", start_date),
        ("endDate", end_date),
    ]
    if club_id:
        params.append(("club_id", club_id))
        params.append(("clubId", club_id))

    timeout = httpx.Timeout(settings.http_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, headers=_headers(), follow_redirects=True) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            body = (e.response.text or "")[:2000]
            raise UpstreamError(
                "Upstream returned non-2xx",
                status_code=e.response.status_code,
                body=body,
                url=str(e.request.url),
                www_authenticate=e.response.headers.get("www-authenticate"),
            ) from e
        except httpx.RequestError as e:
            raise UpstreamError("Upstream request failed", url=str(e.request.url) if e.request else url) from e

    # Ожидаем массив занятий. Если вернулась структура (result/data), пытаемся извлечь.
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "classes", "result"):
            v = data.get(key)
            if isinstance(v, list):
                return v
    raise ValueError("Unexpected response format from 1C Fitness {classes}")

