"""Tests for list_assets CLI helper logic."""

import grpc

from drawthings import list_assets


class _FakeRpcError(grpc.RpcError):
    def __init__(self, code, details):
        super().__init__()
        self._code = code
        self._details = details

    def code(self):
        return self._code

    def details(self):
        return self._details


def test_item_label_prefers_file_key():
    assert list_assets._item_label({"file": "model.ckpt", "name": "Model"}) == "model.ckpt"


def test_item_label_falls_back_to_name_key():
    assert list_assets._item_label({"name": "Model"}) == "Model"


def test_is_blocked_sampler_supports_dict_and_string():
    assert list_assets._is_blocked_sampler({"api_name": "LCM"}) is True
    assert list_assets._is_blocked_sampler("LCM") is True
    assert list_assets._is_blocked_sampler({"api_name": "UniPC"}) is False


def test_format_rpc_error_for_socket_closed_unavailable():
    exc = _FakeRpcError(
        grpc.StatusCode.UNAVAILABLE,
        "failed to connect to all addresses; last error: UNAVAILABLE: ipv4:127.0.0.1:7859: Socket closed",
    )
    message = list_assets._format_rpc_error(exc)
    assert "Protocol=gRPC" in message
    assert "TLS=On" in message


def test_format_rpc_error_for_server_preface_unavailable():
    exc = _FakeRpcError(
        grpc.StatusCode.UNAVAILABLE,
        "error reading server preface: http2: frame too large",
    )
    message = list_assets._format_rpc_error(exc)
    assert "Protocol=gRPC" in message
    assert "Compression=Off" in message


def test_format_rpc_error_for_network_unreachable_unavailable():
    exc = _FakeRpcError(
        grpc.StatusCode.UNAVAILABLE,
        "dial tcp 127.0.0.1:7859: connect: network is unreachable",
    )
    message = list_assets._format_rpc_error(exc)
    assert "Could not connect to Draw Things gRPC server" in message
    assert "--host" in message


def test_format_rpc_error_default_branch():
    exc = _FakeRpcError(grpc.StatusCode.INVALID_ARGUMENT, "bad request")
    assert list_assets._format_rpc_error(exc) == "gRPC INVALID_ARGUMENT: bad request"