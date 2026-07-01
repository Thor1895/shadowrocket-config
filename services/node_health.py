from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "shadowrocket-config-health-check/1.0"


def request_url(url: str, timeout: float, headers: dict[str, str] | None = None) -> tuple[bool, int | None, str | None]:
    request = Request(url, headers=headers or {"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            response.read(256)
        return 200 <= status < 400, status, None
    except HTTPError as exc:
        return False, exc.code, f"HTTP {exc.code}: {exc.reason}"
    except URLError as exc:
        return False, None, str(exc.reason)
    except TimeoutError:
        return False, None, "request timed out"
    except OSError as exc:
        return False, None, str(exc)
