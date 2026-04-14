"""Tests for image_helpers (tensor encode/decode)."""

import struct
from io import BytesIO
import numpy as np
import pytest
import fpzip
from PIL import Image
from drawthings.image_helpers import convert_response_image, convert_image_for_request


def _make_test_tensor(width, height, channels=3, tensor_type=0):
    """Create a fake DTTensor with known pixel values."""
    header = bytearray(68)
    struct.pack_into("<I", header, 0, tensor_type)
    struct.pack_into("<I", header, 6 * 4, height)
    struct.pack_into("<I", header, 7 * 4, width)
    struct.pack_into("<I", header, 8 * 4, channels)

    # Use 0.0 float16 values -> should decode to 127
    f16 = np.zeros(width * height * channels, dtype=np.float16)
    return bytes(header) + f16.tobytes()


def _make_compressed_tensor(width, height, channels=3):
    """Create a fake compressed DTTensor."""
    header = bytearray(68)
    struct.pack_into("<I", header, 0, 1012247)  # COMPRESSED_TENSOR_TYPE
    struct.pack_into("<I", header, 6 * 4, height)
    struct.pack_into("<I", header, 7 * 4, width)
    struct.pack_into("<I", header, 8 * 4, channels)

    # Create float32 data and compress with fpzip
    f32_data = np.zeros((height, width, channels), dtype=np.float32)
    compressed = fpzip.compress(f32_data, order="C")
    return bytes(header) + compressed


def test_convert_response_image_dimensions():
    tensor = _make_test_tensor(64, 48, 3)
    img = convert_response_image(tensor)
    assert img.size == (64, 48)
    assert img.mode == "RGB"


def test_convert_response_image_pixel_values():
    tensor = _make_test_tensor(2, 2, 3)
    img = convert_response_image(tensor)
    arr = np.array(img)
    # float16 value 0.0 -> (0 + 1) * 127 = 127
    assert np.all(arr == 127)


def test_convert_response_image_4channel():
    tensor = _make_test_tensor(4, 4, 4)
    img = convert_response_image(tensor)
    assert img.size == (4, 4)
    assert img.mode == "RGB"


def test_convert_image_for_request_roundtrip():
    # Create a simple test image
    arr = np.full((32, 32, 3), 127, dtype=np.uint8)
    img = Image.fromarray(arr, "RGB")

    tensor = convert_image_for_request(img)
    assert isinstance(tensor, bytes)
    assert len(tensor) == 68 + 32 * 32 * 3 * 2  # header + float16 payload

    # Verify header
    header = struct.unpack_from("<17I", tensor, 0)
    assert header[6] == 32  # height
    assert header[7] == 32  # width
    assert header[8] == 3   # channels


def test_convert_image_for_request_resize():
    arr = np.full((100, 200, 3), 127, dtype=np.uint8)
    img = Image.fromarray(arr, "RGB")

    tensor = convert_image_for_request(img, width=64, height=64)
    header = struct.unpack_from("<17I", tensor, 0)
    assert header[6] == 64
    assert header[7] == 64


def test_convert_response_image_rejects_unsupported_channel_count():
    tensor = _make_test_tensor(64, 64, 16)
    with pytest.raises(ValueError, match="Unsupported DTTensor channel count"):
        convert_response_image(tensor)


def test_convert_response_image_rejects_incomplete_payload():
    header = bytearray(68)
    struct.pack_into("<I", header, 6 * 4, 8)
    struct.pack_into("<I", header, 7 * 4, 8)
    struct.pack_into("<I", header, 8 * 4, 3)
    tensor = bytes(header) + (b"\x00" * 10)

    with pytest.raises(ValueError, match="Incomplete DTTensor payload"):
        convert_response_image(tensor)


def test_convert_response_image_handles_compressed_tensor():
    """Compressed DTTensor payloads are now decompressed via fpzip."""
    tensor = _make_compressed_tensor(8, 8, 3)
    img = convert_response_image(tensor)
    assert img.size == (8, 8)
    assert img.mode == "RGB"


def test_convert_response_image_accepts_png_bytes():
    src = Image.new("RGB", (6, 4), color=(10, 20, 30))
    buf = BytesIO()
    src.save(buf, format="PNG")

    img = convert_response_image(buf.getvalue())
    assert img.size == (6, 4)
    assert img.mode == "RGB"


def test_convert_response_image_handles_raw_rgb_payload_after_header():
    width, height = 2, 2
    header = bytearray(68)
    struct.pack_into("<I", header, 6 * 4, height)
    struct.pack_into("<I", header, 7 * 4, width)
    struct.pack_into("<I", header, 8 * 4, 3)

    # Raw packed RGB payload (not float16 tensor bytes)
    payload = bytes([
        255, 0, 0,
        0, 255, 0,
        0, 0, 255,
        255, 255, 255,
    ])

    img = convert_response_image(bytes(header) + payload)
    assert img.size == (2, 2)
    assert img.mode == "RGB"


def test_convert_image_for_request_always_encodes_rgb_tensor():
    rgba = Image.new("RGBA", (5, 7), color=(1, 2, 3, 255))
    tensor = convert_image_for_request(rgba)
    header = struct.unpack_from("<17I", tensor, 0)
    assert header[6] == 7
    assert header[7] == 5
    assert header[8] == 3
