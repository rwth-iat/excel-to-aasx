"""Diagram rendering for the live preview (ADR 0011), with a fake renderer."""

import threading

from excel_to_aasx.domain.diagram_source import RendererBusy
from tests.adapters.test_web import _app, _upload
from tests.demo import DEMO


def _workspace(client) -> str:
    return _upload(client, DEMO).json()["id"]


def test_diagram_is_rendered_as_sandboxed_svg(tmp_path):
    client, _ = _app(tmp_path)
    response = client.post(f"/api/workspaces/{_workspace(client)}/diagram", content="class A")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert response.headers["content-security-policy"].startswith("sandbox")
    assert response.content == b"<svg><text>7</text></svg>"


def test_diagram_needs_a_workspace_and_a_small_body(tmp_path):
    client, _ = _app(tmp_path, max_diagram_bytes=10)
    assert client.post("/api/workspaces/" + "0" * 32 + "/diagram", content="x").status_code == 404
    workspace = _workspace(client)
    assert client.post(f"/api/workspaces/{workspace}/diagram", content="x" * 11).status_code == 413


def test_diagram_failure_is_reported(tmp_path):
    client, _ = _app(tmp_path)
    response = client.post(f"/api/workspaces/{_workspace(client)}/diagram", content="boom")
    assert response.status_code == 422 and "boom" in response.json()["detail"]


def test_one_session_gets_one_render_at_a_time_and_a_gap(tmp_path):
    client, _ = _app(tmp_path)
    url = f"/api/workspaces/{_workspace(client)}/diagram"
    assert client.post(url, content="class A").status_code == 200
    second = client.post(url, content="class B")
    assert second.status_code == 429 and "wait a moment" in second.json()["detail"]


def test_busy_renderer_answers_429(tmp_path):
    started, release = threading.Event(), threading.Event()

    def slow(_source: str) -> bytes:
        started.set()
        release.wait(5)
        return b"<svg/>"

    client, _ = _app(tmp_path, render_diagram=slow, parallel_diagrams=1, max_count=5)
    first_url = f"/api/workspaces/{_workspace(client)}/diagram"
    other_url = f"/api/workspaces/{_workspace(client)}/diagram"
    first = threading.Thread(target=lambda: client.post(first_url, content="a"))
    first.start()
    assert started.wait(5)
    try:
        response = client.post(other_url, content="b")
        assert response.status_code == 429 and "busy" in response.json()["detail"]
    finally:
        release.set()
        first.join()


def test_busy_diagram_service_answers_429(tmp_path):
    def busy(_source: str) -> bytes:
        raise RendererBusy("the diagram renderer is busy")

    client, _ = _app(tmp_path, render_diagram=busy)
    response = client.post(f"/api/workspaces/{_workspace(client)}/diagram", content="a")
    assert response.status_code == 429
