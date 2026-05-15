from datetime import datetime
from typing import Any

import httpx


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
CAL_API_BASE = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarClient:
    def __init__(self, access_token: str, *, http: httpx.AsyncClient | None = None):
        self.access_token = access_token
        self._http = http or httpx.AsyncClient(timeout=15)

    async def list_events(
        self,
        *,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
    ) -> list[dict[str, Any]]:
        params = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 250,
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"{CAL_API_BASE}/calendars/{calendar_id}/events"
        resp = await self._http.get(url, params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

        out = []
        for item in payload.get("items", []):
            start_raw = item.get("start", {})
            end_raw = item.get("end", {})
            start_at = _parse_dt(start_raw.get("dateTime") or start_raw.get("date"))
            end_at = _parse_dt(end_raw.get("dateTime") or end_raw.get("date")) if end_raw else None
            if start_at is None:
                continue
            out.append({
                "id": item["id"],
                "summary": item.get("summary", "(제목 없음)"),
                "start_at": start_at,
                "end_at": end_at,
                "description": item.get("description"),
            })
        return out


async def exchange_refresh_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    http: httpx.AsyncClient | None = None,
) -> str:
    http = http or httpx.AsyncClient(timeout=15)
    resp = await http.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # all-day events come as "YYYY-MM-DD"; treat as UTC midnight for simplicity
    if len(value) == 10:
        return datetime.fromisoformat(value + "T00:00:00+00:00")
    return datetime.fromisoformat(value).astimezone()
