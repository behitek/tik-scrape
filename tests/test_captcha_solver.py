import pytest

from scraper.captcha_solver import (
    CaptchaSolver, CaptchaSolverError, SolveResult, _strip_data_uri,
)
from scraper.tiktok_scraper import _drag_distance


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]):
        self._responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json))
        return self._responses.pop(0)


def _solver(responses: list[_FakeResponse]) -> tuple[CaptchaSolver, _FakeSession]:
    session = _FakeSession(responses)
    solver = CaptchaSolver(
        "sk_test", session=session, poll_interval=0, timeout=1,
    )
    return solver, session


def test_strip_data_uri_accepts_raw_and_data_uris():
    assert _strip_data_uri("abc123") == "abc123"
    assert _strip_data_uri("data:image/png;base64,abc123") == "abc123"
    assert _strip_data_uri("") == ""


def test_solve_result_normalises_known_fields():
    result = SolveResult(
        {"x": 362, "target_x": 362, "distance": 362, "proportion": 0.656, "angle": 90}
    )
    assert result.x == 362
    assert result.proportion == 0.656
    assert result.angle == 90
    assert SolveResult({"distance": 12.5}).x == 12.5
    assert SolveResult({}).x is None


def test_solve_tiktok_returns_immediate_solution_and_sends_expected_payload():
    solver, session = _solver([
        _FakeResponse({
            "status": 1, "errorId": 0,
            "solution": {"x": 362, "proportion": 0.656},
        }),
    ])

    result = solver.solve_tiktok(
        "data:image/jpeg;base64,IMAGEDATA",
        piece_b64="data:image/png;base64,PIECEDATA",
        subtype="puzzle",
    )

    assert result.x == 362
    url, payload = session.calls[0]
    assert url.endswith("/api/solve/createTask")
    assert payload["clientKey"] == "sk_test"
    assert payload["task"] == {
        "type": "TikTokCaptchaTask",
        "image": "IMAGEDATA",
        "piece": "PIECEDATA",
        "subtype": "puzzle",
    }


def test_solve_tiktok_polls_until_status_ready():
    solver, session = _solver([
        _FakeResponse({"status": 1, "errorId": 0, "taskId": "TASK-1"}),
        _FakeResponse({"status": 0, "errorId": 0}),
        _FakeResponse({
            "status": "ready", "errorId": 0,
            "solution": {"angle": 128},
        }),
    ])

    result = solver.solve_tiktok("IMAGEDATA", subtype="rotate")

    assert result.angle == 128
    assert "piece" not in session.calls[0][1]["task"]
    assert session.calls[1][0].endswith("/api/solve/getTaskResult")
    assert session.calls[1][1]["taskId"] == "TASK-1"


def test_solve_tiktok_raises_on_api_error():
    solver, _ = _solver([
        _FakeResponse({
            "status": 0, "errorId": 1,
            "request": "ERROR_CAPTCHA_UNSUPPORTED",
            "errorDescription": "Loại Captcha không được hỗ trợ",
        }),
    ])

    with pytest.raises(CaptchaSolverError, match="không được hỗ trợ"):
        solver.solve_tiktok("IMAGEDATA")


def test_solve_tiktok_raises_without_key():
    solver = CaptchaSolver("")
    with pytest.raises(CaptchaSolverError, match="API key"):
        solver.solve_tiktok("IMAGEDATA")


def test_get_balance_returns_value_and_raises_on_bad_key():
    solver, session = _solver([
        _FakeResponse({"status": 1, "errorId": 0, "balance": 9933}),
    ])
    assert solver.get_balance() == 9933
    assert session.calls[0][0].endswith("/api/solve/getBalance")

    bad_solver, _ = _solver([
        _FakeResponse({"status": 0, "errorId": 1, "request": "ERROR_KEY_DOES_NOT_EXIST"}),
    ])
    with pytest.raises(CaptchaSolverError, match="ERROR_KEY_DOES_NOT_EXIST"):
        bad_solver.get_balance()


def _puzzle_state(display_w: float = 340.0, natural_w: float = 552.0) -> dict:
    return {
        "imageRect": {"x": 470, "y": 276, "w": display_w, "h": 212},
        "natural": {"w": natural_w, "h": 344},
        "sliderRect": {"x": 470, "y": 492, "w": 340, "h": 44},
        "thumbRect": {"x": 470, "y": 492, "w": 44, "h": 44},
    }


def test_drag_distance_uses_proportion_for_puzzle():
    solution = SolveResult({"x": 362, "proportion": 362 / 552})
    distance = _drag_distance(_puzzle_state(), solution)
    assert distance == pytest.approx(362 / 552 * 340)


def test_drag_distance_scales_natural_pixels_when_proportion_missing():
    solution = SolveResult({"x": 362})
    distance = _drag_distance(_puzzle_state(), solution)
    assert distance == pytest.approx(362 * 340 / 552)


def test_drag_distance_maps_rotate_angle_to_slider_travel():
    solution = SolveResult({"angle": 90})
    distance = _drag_distance(_puzzle_state(), solution)
    assert distance == pytest.approx((340 - 44) * 0.25)


def test_drag_distance_returns_none_for_unknown_solution():
    assert _drag_distance(_puzzle_state(), SolveResult({"objects": [1, 4]})) is None
