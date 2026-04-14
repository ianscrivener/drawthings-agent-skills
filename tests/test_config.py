"""Tests for the config builder (build_config_buffer)."""

import struct
import flatbuffers
from drawthings.config import build_config_buffer, DEFAULT_CONFIG, _round64
from drawthings.generated.GenerationConfiguration import GenerationConfiguration


def test_build_config_buffer_returns_bytes():
    buf = build_config_buffer()
    assert isinstance(buf, bytes)
    assert len(buf) > 68


def test_default_config_roundtrips():
    buf = build_config_buffer()
    cfg = GenerationConfiguration.GetRootAs(buf, 0)
    assert cfg.Steps() == 20
    assert cfg.StartWidth() == 512 // 64
    assert cfg.StartHeight() == 512 // 64
    assert cfg.BatchCount() == 1
    assert cfg.BatchSize() == 1
    assert cfg.Model().decode() == "sd_v1.5_f16.ckpt"
    assert cfg.Upscaler() is None
    assert cfg.FaceRestoration() is None


def test_custom_config_overrides():
    buf = build_config_buffer({"width": 1024, "height": 768, "steps": 30, "model": "test.ckpt"})
    cfg = GenerationConfiguration.GetRootAs(buf, 0)
    assert cfg.StartWidth() == 1024 // 64
    assert cfg.StartHeight() == 768 // 64
    assert cfg.Steps() == 30
    assert cfg.Model().decode() == "test.ckpt"


def test_round64():
    assert _round64(100) == 128
    assert _round64(512) == 512
    assert _round64(500) == 512
    assert _round64(0) == 64
    assert _round64(32) == 64


def test_seed_negative_generates_random():
    buf1 = build_config_buffer({"seed": -1})
    buf2 = build_config_buffer({"seed": -1})
    cfg1 = GenerationConfiguration.GetRootAs(buf1, 0)
    cfg2 = GenerationConfiguration.GetRootAs(buf2, 0)
    # Seeds should both be valid uint32 values (extremely unlikely to match)
    assert cfg1.Seed() > 0 or cfg2.Seed() > 0


def test_fixed_seed():
    buf = build_config_buffer({"seed": 42})
    cfg = GenerationConfiguration.GetRootAs(buf, 0)
    assert cfg.Seed() == 42


def test_loras_in_config():
    buf = build_config_buffer({"loras": [{"file": "test.safetensors", "weight": 0.7}]})
    cfg = GenerationConfiguration.GetRootAs(buf, 0)
    assert cfg.LorasLength() == 1
    assert cfg.Loras(0).File().decode() == "test.safetensors"
    assert abs(cfg.Loras(0).Weight() - 0.7) < 0.01


def test_upscaler_and_face_restoration_fields():
    buf = build_config_buffer(
        {
            "upscaler": "4x_ultrasharp_f16.ckpt",
            "upscaler_scale_factor": 2,
            "face_restoration": "RestoreFormer.pth",
        }
    )
    cfg = GenerationConfiguration.GetRootAs(buf, 0)
    assert cfg.Upscaler().decode() == "4x_ultrasharp_f16.ckpt"
    assert cfg.UpscalerScaleFactor() == 2
    assert cfg.FaceRestoration().decode() == "RestoreFormer.pth"
