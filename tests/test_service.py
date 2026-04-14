"""Tests for DTService (mocked gRPC)."""

import json
import pytest
import grpc
from unittest.mock import MagicMock, call, patch
from drawthings.service import DTService, _parse_signpost


def test_dtservice_init():
    with patch("drawthings.service.grpc.secure_channel") as mock_channel:
        mock_channel.return_value = MagicMock()
        svc = DTService("localhost:7859")
        assert svc.address == "localhost:7859"
        assert svc.use_tls is True
        assert svc.use_compression is False
        mock_channel.assert_called_once()


def test_dtservice_init_insecure():
    with patch("drawthings.service.grpc.insecure_channel") as mock_channel:
        mock_channel.return_value = MagicMock()
        svc = DTService("localhost:7859", use_tls=False)
        assert svc.address == "localhost:7859"
        assert svc.use_tls is False
        assert svc.use_compression is False
        mock_channel.assert_called_once()


def test_dtservice_init_with_compression():
    with patch("drawthings.service.grpc.secure_channel") as mock_channel:
        mock_channel.return_value = MagicMock()
        DTService("localhost:7859", use_compression=True)
        _, kwargs = mock_channel.call_args
        assert kwargs["compression"] == grpc.Compression.Gzip


def test_dtservice_init_insecure_with_compression():
    with patch("drawthings.service.grpc.insecure_channel") as mock_channel:
        mock_channel.return_value = MagicMock()
        DTService("localhost:7859", use_tls=False, use_compression=True)
        _, kwargs = mock_channel.call_args
        assert kwargs["compression"] == grpc.Compression.Gzip


def test_list_assets_decodes_json():
    with patch("drawthings.service.grpc.secure_channel"):
        svc = DTService("localhost:7859")

        mock_reply = MagicMock()
        mock_override = MagicMock()
        mock_override.models = json.dumps([{"file": "sd_v1.5_f16.ckpt", "name": "SD 1.5"}]).encode()
        mock_override.loras = b"[]"
        mock_override.controlNets = b"[]"
        mock_override.upscalers = b"[]"
        mock_override.textualInversions = b"[]"
        mock_reply.override = mock_override

        svc.stub = MagicMock()
        svc.stub.Echo.return_value = mock_reply

        result = svc.list_assets()
        assert len(result["models"]) == 1
        assert result["models"][0]["file"] == "sd_v1.5_f16.ckpt"
        assert result["loras"] == []


def test_parse_signpost_sampling():
    """_parse_signpost extracts stage and step from a sampling signpost."""
    signpost = MagicMock()
    signpost.WhichOneof.return_value = "sampling"
    signpost.sampling.step = 5
    result = _parse_signpost(signpost)
    assert result == {"stage": "sampling", "step": 5}


def test_parse_signpost_no_step():
    """_parse_signpost returns stage only when inner message has no step."""
    signpost = MagicMock()
    signpost.WhichOneof.return_value = "textEncoded"
    inner = MagicMock(spec=[])  # no attributes at all
    signpost.textEncoded = inner
    result = _parse_signpost(signpost)
    assert result == {"stage": "textEncoded"}


def test_parse_signpost_none():
    """_parse_signpost returns None when no signpost field is set."""
    signpost = MagicMock()
    signpost.WhichOneof.return_value = None
    assert _parse_signpost(signpost) is None


def test_generate_calls_progress_callback():
    """generate() calls progress_callback for each signpost in the stream."""
    with patch("drawthings.service.grpc.secure_channel"):
        svc = DTService("localhost:7859")
        svc.stub = MagicMock()

        # Build two mock streaming responses: one signpost, one with image
        # resp1 has signpost but no images, chunkState=0 (continue)
        resp1 = MagicMock()
        resp1.HasField.return_value = True
        signpost1 = MagicMock()
        signpost1.WhichOneof.return_value = "sampling"
        signpost1.sampling.step = 3
        resp1.currentSignpost = signpost1
        resp1.generatedImages = []
        resp1.chunkState = 1

        # resp2 has images, chunkState=0 (last chunk)
        resp2 = MagicMock()
        resp2.HasField.return_value = False
        resp2.generatedImages = [b"\x00" * 100]
        resp2.chunkState = 0

        svc.stub.GenerateImage.return_value = iter([resp1, resp2])

        cb = MagicMock()
        with patch("drawthings.service.convert_response_image") as mock_convert:
            mock_convert.return_value = MagicMock()
            images = svc.generate("test", progress_callback=cb)

        cb.assert_called_once_with({"stage": "sampling", "step": 3})
        assert len(images) == 1


def test_generate_no_callback_skips_progress():
    """generate() works without a progress_callback (no error)."""
    with patch("drawthings.service.grpc.secure_channel"):
        svc = DTService("localhost:7859")
        svc.stub = MagicMock()

        resp = MagicMock()
        resp.HasField.return_value = True
        signpost = MagicMock()
        signpost.WhichOneof.return_value = "textEncoded"
        inner = MagicMock(spec=[])
        signpost.textEncoded = inner
        resp.currentSignpost = signpost
        resp.generatedImages = [b"\x00" * 100]
        resp.chunkState = 0

        svc.stub.GenerateImage.return_value = iter([resp])

        with patch("drawthings.service.convert_response_image") as mock_convert:
            mock_convert.return_value = MagicMock()
            images = svc.generate("test")  # no callback - should not raise

        assert len(images) == 1


def test_generate_passes_timeout_to_rpc():
    """generate() forwards timeout to gRPC when provided."""
    with patch("drawthings.service.grpc.secure_channel"):
        svc = DTService("localhost:7859")
        svc.stub = MagicMock()

        resp = MagicMock()
        resp.HasField.return_value = False
        resp.generatedImages = [b"\x00" * 100]
        resp.chunkState = 0
        svc.stub.GenerateImage.return_value = iter([resp])

        with patch("drawthings.service.convert_response_image") as mock_convert:
            mock_convert.return_value = MagicMock()
            images = svc.generate("test", timeout=12.5)

        assert len(images) == 1
        args, kwargs = svc.stub.GenerateImage.call_args
        assert args[0].chunked is True
        assert kwargs["timeout"] == 12.5


def test_generate_deadline_exceeded_raises_timeout_error():
    """gRPC DEADLINE_EXCEEDED is translated to TimeoutError."""
    with patch("drawthings.service.grpc.secure_channel"):
        svc = DTService("localhost:7859")
        svc.stub = MagicMock()

        class DeadlineExceeded(grpc.RpcError):
            def code(self):
                return grpc.StatusCode.DEADLINE_EXCEEDED

        svc.stub.GenerateImage.side_effect = DeadlineExceeded()

        with pytest.raises(TimeoutError, match="timed out"):
            svc.generate("test", timeout=1.0)


def test_generate_assembles_image_chunks_when_streamed():
    """generate() joins MORE_CHUNKS + LAST_CHUNK payloads before decoding."""
    with patch("drawthings.service.grpc.secure_channel"):
        svc = DTService("localhost:7859")
        svc.stub = MagicMock()

        resp1 = MagicMock()
        resp1.HasField.return_value = False
        resp1.generatedImages = [b"first-"]
        resp1.chunkState = 1  # MORE_CHUNKS

        resp2 = MagicMock()
        resp2.HasField.return_value = False
        resp2.generatedImages = [b"second"]
        resp2.chunkState = 0  # LAST_CHUNK

        svc.stub.GenerateImage.return_value = iter([resp1, resp2])

        with patch("drawthings.service.convert_response_image") as mock_convert:
            mock_convert.return_value = MagicMock()
            images = svc.generate("test")

        assert len(images) == 1
        mock_convert.assert_called_once_with(b"first-second")


def test_generate_flushes_pending_chunks_when_stream_ends():
    """If stream ends after MORE_CHUNKS responses, pending chunks are still decoded."""
    with patch("drawthings.service.grpc.secure_channel"):
        svc = DTService("localhost:7859")
        svc.stub = MagicMock()

        resp = MagicMock()
        resp.HasField.return_value = False
        resp.generatedImages = [b"trailing"]
        resp.chunkState = 1  # MORE_CHUNKS with no explicit LAST_CHUNK after

        svc.stub.GenerateImage.return_value = iter([resp])

        with patch("drawthings.service.convert_response_image") as mock_convert:
            mock_convert.return_value = MagicMock()
            images = svc.generate("test")

        assert len(images) == 1
        mock_convert.assert_called_once_with(b"trailing")


def test_generate_falls_back_to_preview_image_when_no_generated_images():
    """If generatedImages are missing, decode the last previewImage frame."""
    with patch("drawthings.service.grpc.secure_channel"):
        svc = DTService("localhost:7859")
        svc.stub = MagicMock()

        resp1 = MagicMock()
        resp1.HasField.side_effect = lambda name: name == "previewImage"
        resp1.previewImage = b"preview-first"
        resp1.generatedImages = []
        resp1.chunkState = 0

        resp2 = MagicMock()
        resp2.HasField.side_effect = lambda name: name == "previewImage"
        resp2.previewImage = b"preview-last"
        resp2.generatedImages = []
        resp2.chunkState = 0

        svc.stub.GenerateImage.return_value = iter([resp1, resp2])

        with patch("drawthings.service.convert_response_image") as mock_convert:
            mock_convert.return_value = MagicMock()
            images = svc.generate("test")

        assert len(images) == 1
        mock_convert.assert_called_once_with(b"preview-last")


def test_generate_raises_clear_error_when_no_images():
    """If no images are returned, raise a clear error."""
    with patch("drawthings.service.grpc.secure_channel"):
        svc = DTService("localhost:7859")
        svc.stub = MagicMock()

        resp = MagicMock()
        resp.HasField.return_value = False
        resp.generatedImages = []
        resp.chunkState = 1

        svc.stub.GenerateImage.return_value = iter([resp])

        with pytest.raises(ValueError, match="did not return a decodable final image"):
            svc.generate("test")


def test_generate_forwards_upscaler_and_face_restore_into_config():
    with patch("drawthings.service.grpc.secure_channel"):
        svc = DTService("localhost:7859")
        svc.stub = MagicMock()

        resp = MagicMock()
        resp.HasField.return_value = False
        resp.generatedImages = [b"\x00" * 100]
        resp.chunkState = 0
        svc.stub.GenerateImage.return_value = iter([resp])

        with patch("drawthings.service.build_config_buffer") as mock_cfg_buf:
            mock_cfg_buf.return_value = b"cfg"
            with patch("drawthings.service.convert_response_image") as mock_convert:
                mock_convert.return_value = MagicMock()
                svc.generate(
                    "test",
                    upscaler="4x_ultrasharp_f16.ckpt",
                    upscaler_scale_factor=2,
                    face_restoration="RestoreFormer.pth",
                )

        c = mock_cfg_buf.call_args[0][0]
        assert c["upscaler"] == "4x_ultrasharp_f16.ckpt"
        assert c["upscaler_scale_factor"] == 2
        assert c["face_restoration"] == "RestoreFormer.pth"
