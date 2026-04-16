"""Tests for generate.py CLI behavior."""

import json
import sys
from unittest.mock import MagicMock, patch

import grpc
import pytest

from drawthings import generate


class _FakeRpcError(grpc.RpcError):
    def __init__(self, code, details):
        super().__init__()
        self._code = code
        self._details = details

    def code(self):
        return self._code

    def details(self):
        return self._details


def test_main_checks_model_list_before_generating(monkeypatch, capsys, tmp_path):
    svc = MagicMock()
    svc.list_assets.return_value = {"models": [{"file": "foo.ckpt"}]}
    image = MagicMock()
    svc.generate.return_value = [image]

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate.py",
            "--prompt",
            "an apple",
            "--model",
            "foo.ckpt",
            "--output_dir",
            str(tmp_path),
        ],
    )

    with patch("drawthings.service.DTService", return_value=svc):
        generate.main()

    svc.list_assets.assert_called_once()
    svc.generate.assert_called_once()
    image.save.assert_called_once()

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["success"] is True


def test_main_blocks_generation_when_model_unavailable(monkeypatch, capsys, tmp_path):
    svc = MagicMock()
    svc.list_assets.return_value = {
        "models": [{"file": "z_image_turbo_1.0_i8x.ckpt"}, {"file": "flux_qwen_srpo_v1.0_f16.ckpt"}]
    }

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate.py",
            "--prompt",
            "an apple",
            "--model",
            "foo.ckpt",
            "--output_dir",
            str(tmp_path),
        ],
    )

    with patch("drawthings.service.DTService", return_value=svc):
        with pytest.raises(SystemExit) as exc:
            generate.main()

    assert exc.value.code == 1
    svc.list_assets.assert_called_once()
    svc.generate.assert_not_called()

    payload = json.loads(capsys.readouterr().err.strip())
    assert payload["success"] is False
    assert "Requested model 'foo.ckpt' is not available" in payload["error"]
    assert "list_assets.py --type models" in payload["error"]


def test_main_reports_server_unavailable_during_model_validation(monkeypatch, capsys, tmp_path):
    svc = MagicMock()
    svc.list_assets.side_effect = _FakeRpcError(
        grpc.StatusCode.UNAVAILABLE,
        "failed to connect to all addresses; last error: connect: connection refused",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate.py",
            "--prompt",
            "an apple",
            "--model",
            "foo.ckpt",
            "--output_dir",
            str(tmp_path),
        ],
    )

    with patch("drawthings.service.DTService", return_value=svc):
        with pytest.raises(SystemExit) as exc:
            generate.main()

    assert exc.value.code == 1
    svc.list_assets.assert_called_once()
    svc.generate.assert_not_called()

    payload = json.loads(capsys.readouterr().err.strip())
    assert payload["success"] is False
    assert "Could not connect to Draw Things gRPC server" in payload["error"]
