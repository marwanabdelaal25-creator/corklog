"""Tests for corklog.server."""

import json
from unittest.mock import MagicMock, patch

import pytest
from corklog.bottle import Bottle
from corklog.server import CorklogHandler, serve


def _handler(store, path="/health"):
    handler = CorklogHandler(MagicMock(), ("127.0.0.1", 12345), None)
    handler.store = store
    handler.path = path
    handler.wfile = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


def test_health_endpoint(library_store):
    h = _handler(library_store, "/health")
    h.do_GET()
    body = h.wfile.write.call_args[0][0]
    assert json.loads(body.decode())["ok"] is True


def test_bottles_list(library_store, sample_bottle):
    library_store.upsert_bottle(sample_bottle)
    h = _handler(library_store, "/bottles")
    h.do_GET()
    body = json.loads(h.wfile.write.call_args[0][0].decode())
    assert len(body) == 1


def test_bottles_limit(library_store, bottles_batch):
    for b in bottles_batch:
        library_store.upsert_bottle(b)
    h = _handler(library_store, "/bottles?limit=2")
    h.do_GET()
    body = json.loads(h.wfile.write.call_args[0][0].decode())
    assert len(body) == 2


def test_bottle_detail(library_store, sample_bottle):
    library_store.upsert_bottle(sample_bottle)
    h = _handler(library_store, f"/bottles/{sample_bottle.id}")
    h.do_GET()
    body = json.loads(h.wfile.write.call_args[0][0].decode())
    assert body["title"] == sample_bottle.title


def test_bottle_not_found(library_store):
    h = _handler(library_store, "/bottles/missing-id")
    h.do_GET()
    assert h.send_response.call_args[0][0] == 404


def test_stats_route(library_store, sample_bottle):
    library_store.upsert_bottle(sample_bottle)
    h = _handler(library_store, "/stats")
    h.do_GET()
    body = json.loads(h.wfile.write.call_args[0][0].decode())
    assert "status" in body


def test_unknown_route(library_store):
    h = _handler(library_store, "/nope")
    h.do_GET()
    assert h.send_response.call_args[0][0] == 404


def test_json_content_type(library_store):
    h = _handler(library_store, "/health")
    h.do_GET()
    headers = [c[0][0] for c in h.send_header.call_args_list]
    assert "Content-Type" in headers


def test_log_message_suppressed(library_store):
    h = _handler(library_store)
    h.log_message("fmt %s", "x")  # no raise


def test_serve_keyboard_interrupt(library_store):
    httpd = MagicMock()
    httpd.serve_forever.side_effect = KeyboardInterrupt
    with patch("corklog.server.HTTPServer", return_value=httpd):
        serve(library_store, port=9999)  # should exit cleanly


def test_handler_bound_store(library_store):
    h = _handler(library_store)
    assert h.store is library_store


def test_bottles_empty(library_store):
    h = _handler(library_store, "/bottles")
    h.do_GET()
    body = json.loads(h.wfile.write.call_args[0][0].decode())
    assert body == []


def test_content_length_header(library_store):
    h = _handler(library_store, "/health")
    h.do_GET()
    header_names = [call[0][0] for call in h.send_header.call_args_list]
    assert "Content-Length" in header_names


def test_stats_avg_rating_key(library_store, sample_bottle):
    library_store.upsert_bottle(sample_bottle)
    h = _handler(library_store, "/stats")
    h.do_GET()
    body = json.loads(h.wfile.write.call_args[0][0].decode())
    assert "avg_rating" in body


def test_bottle_detail_200(library_store, sample_bottle):
    library_store.upsert_bottle(sample_bottle)
    h = _handler(library_store, f"/bottles/{sample_bottle.id}")
    h.do_GET()
    assert h.send_response.call_args[0][0] == 200


def test_health_200(library_store):
    h = _handler(library_store, "/health")
    h.do_GET()
    assert h.send_response.call_args[0][0] == 200


def test_serve_prints(capsys, library_store):
    httpd = MagicMock()
    httpd.serve_forever.side_effect = KeyboardInterrupt
    with patch("corklog.server.HTTPServer", return_value=httpd):
        serve(library_store, host="127.0.0.1", port=8888)
    out = capsys.readouterr().out
    assert "8888" in out
