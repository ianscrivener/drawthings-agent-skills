# Testing Guide

This project uses `pytest` for unit tests.

Current suite status:

- 46 unit tests
- 5 test files in `tests/`
- Tests are mocked and do not require a running Draw Things server

## Prerequisites

Use `uv` for dependency management.

```bash
uv sync --group dev
source .venv/bin/activate
```

## Run All Tests

```bash
pytest
```

With explicit coverage output:

```bash
pytest -v --cov=src/drawthings --cov-report=term-missing
```

## Run Specific Test Files

```bash
pytest tests/test_config.py -v
pytest tests/test_generate.py -v
pytest tests/test_image_helpers.py -v
pytest tests/test_list_assets.py -v
pytest tests/test_service.py -v
```

## Run A Single Test

```bash
pytest tests/test_service.py::test_generate_deadline_exceeded_raises_timeout_error -v
```

## Currently Implemented Tests

### `tests/test_config.py` (8 tests)

- `test_build_config_buffer_returns_bytes`: config builder returns bytes with non-empty payload.
- `test_default_config_roundtrips`: default config values deserialize correctly from FlatBuffer.
- `test_custom_config_overrides`: custom width/height/steps/model values override defaults.
- `test_round64`: width/height rounding helper behavior.
- `test_seed_negative_generates_random`: negative seed path generates randomized seed values.
- `test_fixed_seed`: fixed seed is preserved.
- `test_loras_in_config`: LoRA list serializes into config.
- `test_upscaler_and_face_restoration_fields`: upscaler and face restoration fields serialize correctly.

### `tests/test_generate.py` (3 tests)

- `test_main_checks_model_list_before_generating`: preflight model list check runs before generation and allows valid model requests.
- `test_main_blocks_generation_when_model_unavailable`: generation is blocked and an actionable message is returned when requested model is missing.
- `test_main_reports_server_unavailable_during_model_validation`: server-unavailable during preflight returns a connectivity-focused error message.

### `tests/test_image_helpers.py` (11 tests)

- `test_convert_response_image_dimensions`: decoded image dimensions and mode from tensor.
- `test_convert_response_image_pixel_values`: float16 tensor pixel mapping to image values.
- `test_convert_response_image_4channel`: 4-channel tensors decode to RGB image output.
- `test_convert_image_for_request_roundtrip`: request tensor encoding shape/header correctness.
- `test_convert_image_for_request_resize`: resize arguments are reflected in encoded tensor header.
- `test_convert_response_image_rejects_unsupported_channel_count`: invalid channel counts raise clear errors.
- `test_convert_response_image_rejects_incomplete_payload`: truncated tensor payload raises clear errors.
- `test_convert_response_image_handles_compressed_tensor`: compressed fpzip tensors are decoded.
- `test_convert_response_image_accepts_png_bytes`: PNG bytes path is accepted and decoded.
- `test_convert_response_image_handles_raw_rgb_payload_after_header`: raw RGB payload fallback after header works.
- `test_convert_image_for_request_always_encodes_rgb_tensor`: non-RGB input is encoded as RGB tensor.

### `tests/test_list_assets.py` (7 tests)

- `test_item_label_prefers_file_key`: item label uses `file` key when present.
- `test_item_label_falls_back_to_name_key`: item label falls back to `name`.
- `test_is_blocked_sampler_supports_dict_and_string`: blocked sampler detection handles dict and string values.
- `test_format_rpc_error_for_socket_closed_unavailable`: socket-closed unavailable errors map to guidance text.
- `test_format_rpc_error_for_server_preface_unavailable`: server-preface/handshake style unavailable errors map to protocol guidance text.
- `test_format_rpc_error_for_network_unreachable_unavailable`: network-unreachable unavailable errors map to connectivity guidance text.
- `test_format_rpc_error_default_branch`: generic gRPC errors map to default format.

### `tests/test_service.py` (17 tests)

- `test_dtservice_init`: secure channel default initialization.
- `test_dtservice_init_insecure`: insecure channel initialization.
- `test_dtservice_init_with_compression`: secure channel compression argument.
- `test_dtservice_init_insecure_with_compression`: insecure channel compression argument.
- `test_list_assets_decodes_json`: `Echo` asset payload JSON decode path.
- `test_parse_signpost_sampling`: sampling signpost parsing with step.
- `test_parse_signpost_no_step`: signpost parsing without step field.
- `test_parse_signpost_none`: signpost parsing when no signpost is present.
- `test_generate_calls_progress_callback`: progress callback invoked with parsed signpost updates.
- `test_generate_no_callback_skips_progress`: generate path works without callback.
- `test_generate_passes_timeout_to_rpc`: timeout forwarded to gRPC call.
- `test_generate_deadline_exceeded_raises_timeout_error`: deadline exceeded translated to `TimeoutError`.
- `test_generate_assembles_image_chunks_when_streamed`: chunked image fragments are assembled before decode.
- `test_generate_flushes_pending_chunks_when_stream_ends`: trailing buffered chunks are flushed at stream end.
- `test_generate_falls_back_to_preview_image_when_no_generated_images`: preview image fallback decode path.
- `test_generate_raises_clear_error_when_no_images`: clear error when no decodable final image exists.
- `test_generate_forwards_upscaler_and_face_restore_into_config`: upscaler and face restoration options forwarded to config builder.