# Capability Matrix

| Capability | Current Beta status | Implementations | Notes |
| --- | --- | --- | --- |
| `text.reason` | NOT_AVAILABLE | 0 | Register a real reasoning service before enabling |
| `code` | NOT_AVAILABLE | 0 | No fake executor is installed |
| `web.research` | NOT_AVAILABLE | 0 | Requires a permission-scoped research tool |
| `image.generate` | NOT_AVAILABLE | 0 | Provider implementation not onboarded |
| `image.edit` | NOT_AVAILABLE | 0 | Provider implementation not onboarded |
| `vision.analyze` | NOT_AVAILABLE | 0 | Provider implementation not onboarded |
| `audio.transcribe` | NOT_AVAILABLE | 0 | Provider implementation not onboarded |
| `speech.synthesize` | NOT_AVAILABLE | 0 | Provider implementation not onboarded |
| `video.generate` | NOT_AVAILABLE | 0 | Provider implementation not onboarded |
| `document.read` | NOT_AVAILABLE | 0 | Register a real document service before enabling |
| `document.write` | NOT_AVAILABLE | 0 | Register a real document service before enabling |
| `file.read` | NOT_AVAILABLE | 0 | Register a real workspace tool before enabling |
| `file.write` | NOT_AVAILABLE | 0 | Register a real workspace tool before enabling |
| `local.execute` | NOT_AVAILABLE | 0 | Requires an isolated, permission-scoped worker |

This matrix describes the default WebCore registry. Test executors are only
used in `tests/test_capability_layer.py` to prove routing behavior and are not
production capability implementations.
