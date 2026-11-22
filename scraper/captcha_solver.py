"""Client for the CaptchaSolve API (captcha.kimidev.net).

The service is 2captcha-compatible: create a task, then poll for the result.
TikTok challenges are submitted as ``TikTokCaptchaTask`` with a base64 image
(and, for puzzle challenges, the base64 puzzle piece).
"""

import logging
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.kimidev.net"

# TikTok challenge subtypes supported by the service.
SUBTYPE_PUZZLE = "puzzle"
SUBTYPE_ROTATE = "rotate"
SUBTYPE_3D = "3d"
SUBTYPE_TWO_OBJECTS = "two_objects"

_SUPPORTED_SUBTYPES = {
    SUBTYPE_PUZZLE,
    SUBTYPE_ROTATE,
    SUBTYPE_3D,
    SUBTYPE_TWO_OBJECTS,
}

_ERROR_PROCESSING = 0


class CaptchaSolverError(Exception):
    """The resolver rejected a task or did not produce a solution in time."""


@dataclass
class SolveResult:
    """A solved TikTok challenge.

    ``raw`` is the untouched ``solution`` object from the API. The helpers
    below normalise the fields the UI code needs.
    """

    raw: dict

    @property
    def x(self) -> float | None:
        for key in ("x", "distance", "offset", "slide", "targetX"):
            value = self.raw.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    @property
    def y(self) -> float | None:
        for key in ("y", "targetY"):
            value = self.raw.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    @property
    def angle(self) -> float | None:
        for key in ("angle", "rotation", "degrees"):
            value = self.raw.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    @property
    def proportion(self) -> float | None:
        """Target position as a fraction of the challenge image width."""
        value = self.raw.get("proportion")
        if isinstance(value, (int, float)):
            return float(value)
        return None


class CaptchaSolver:
    """Minimal createTask/getTaskResult client for CaptchaSolve."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        session: requests.Session | None = None,
        poll_interval: float = 1.5,
        timeout: float = 120.0,
    ):
        self._api_key = (api_key or "").strip()
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._session = session or requests.Session()
        self._poll_interval = poll_interval
        self._timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _post(self, path: str, payload: dict, timeout: float = 30.0) -> dict:
        url = f"{self._base_url}{path}"
        try:
            resp = self._session.post(url, json=payload, timeout=timeout)
        except requests.RequestException as e:
            raise CaptchaSolverError(f"Không kết nối được máy chủ CAPTCHA: {e}") from e
        if resp.status_code >= 400:
            raise CaptchaSolverError(
                f"Máy chủ CAPTCHA trả về HTTP {resp.status_code}: {resp.text[:160]}"
            )
        try:
            return resp.json()
        except ValueError as e:
            raise CaptchaSolverError(
                f"Phản hồi CAPTCHA không phải JSON: {resp.text[:160]}"
            ) from e

    @staticmethod
    def _raise_for_error(data: dict) -> None:
        if data.get("errorId") not in (None, _ERROR_PROCESSING):
            description = data.get("errorDescription") or data.get("request") or "unknown error"
            raise CaptchaSolverError(f"API CAPTCHA báo lỗi: {description}")

    def get_balance(self) -> float:
        """Return the account balance (raises CaptchaSolverError on bad keys)."""
        data = self._post("/api/solve/getBalance", {"clientKey": self._api_key})
        self._raise_for_error(data)
        if data.get("status") != 1:
            raise CaptchaSolverError("Không đọc được số dư tài khoản CAPTCHA")
        return float(data.get("balance", 0))

    def solve_tiktok(
        self,
        image_b64: str,
        piece_b64: str | None = None,
        subtype: str | None = None,
    ) -> SolveResult:
        """Solve one TikTok challenge and return the normalised solution.

        ``image_b64`` is the main/background challenge image; ``piece_b64`` is
        the draggable puzzle piece for slider challenges.
        """
        if not self.configured:
            raise CaptchaSolverError("Chưa cấu hình API key CAPTCHA")
        if not image_b64:
            raise CaptchaSolverError("Không có ảnh CAPTCHA để gửi đi giải")

        task: dict = {"type": "TikTokCaptchaTask", "image": _strip_data_uri(image_b64)}
        if piece_b64:
            task["piece"] = _strip_data_uri(piece_b64)
        if subtype in _SUPPORTED_SUBTYPES:
            task["subtype"] = subtype

        logger.info(
            "Gửi CAPTCHA TikTok lên máy chủ (subtype=%s, ảnh %d ký tự, mảnh ghép=%s)",
            subtype or "auto", len(image_b64), "có" if piece_b64 else "không",
        )
        started = time.monotonic()
        data = self._post(
            "/api/solve/createTask",
            {"clientKey": self._api_key, "task": task},
        )
        self._raise_for_error(data)

        solution = data.get("solution")
        if solution:
            logger.info("CAPTCHA được giải ngay (%.1fs): %s", time.monotonic() - started, solution)
            return SolveResult(solution)

        task_id = data.get("taskId")
        if not task_id:
            raise CaptchaSolverError(
                "Máy chủ CAPTCHA không trả về taskId "
                f"({data.get('errorDescription') or data.get('request') or data})"
            )

        deadline = started + self._timeout
        while time.monotonic() < deadline:
            time.sleep(self._poll_interval)
            result = self._post(
                "/api/solve/getTaskResult",
                {"clientKey": self._api_key, "taskId": task_id},
            )
            self._raise_for_error(result)
            solution = result.get("solution")
            # The service returns status: "ready" once a solution exists
            # (a literal 1 is also accepted for 2captcha compatibility).
            if solution and result.get("status") in (1, "ready", True):
                logger.info(
                    "CAPTCHA được giải sau %.1fs: %s",
                    time.monotonic() - started, solution,
                )
                return SolveResult(solution)

        raise CaptchaSolverError(
            f"Hết thời gian chờ giải CAPTCHA ({self._timeout:.0f}s)"
        )


def _strip_data_uri(value: str) -> str:
    """Accept raw base64 or a data: URI and return bare base64."""
    value = (value or "").strip()
    if value.startswith("data:") and "," in value:
        return value.split(",", 1)[1]
    return value
