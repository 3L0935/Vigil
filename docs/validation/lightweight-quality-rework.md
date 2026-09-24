# Lightweight quality rework: validation record

Date: 2026-09-24. Baseline checkout: `c3e87ac`; implementation branch:
`feat/lightweight-quality-rework`. The local evaluation scripts and sanitized
fixtures used for this record were temporary and are not part of the product.
The aggregate observations below are retained for review.

## Environment and method

- Linux x86_64, AMD RX 7900 XT. Managed `llama-server` 0.4.1-dev, build
  11120, commit `08b1d2aea`, on loopback; 8192-token context, 99 configured
  GPU layers. Installed `LFM2.5-2.6B-Q4_K_M.gguf` (Q4_K_M quantization).
  The server's installed chat template was used. Requests used the compatible
  default profile, `parallel_tool_calls=false`, 512 output tokens for the first
  assistant request and 384 for search synthesis. The optional model-specific
  sampling profile was not enabled for these comparisons.
- Speech setup: configured `medium` Whisper model, CPU/int8, beam size 5,
  VAD enabled. Speech inference was not benchmarked because no consented audio
  was available. The STT model, VAD, beam size and device defaults are unchanged.
- A temporary, side-effect-free intent runner used 24 sanitized assistant
  cases, including six holdouts. Each case was run three times against both
  checkouts with the same installed model and server configuration. The runner
  only inspected proposed tool calls; it did not launch apps, open URLs, paste,
  or write settings. Web tools were advertised inside the runner to test
  routing without changing the persisted web policy.
- Twelve reference utterances, including four holdouts, were prepared without
  audio. Their absence prevents WER, critical-token and STT latency claims.
  A temporary paired beam 1/5 runner rejected execution when audio was absent.
- Timings use `time.perf_counter`; memory is process-tree RSS sampled during
  evaluation, and GPU usage is system-wide VRAM from sysfs. Sample counts are
  small. Maximum and median times describe this run, not a stable p95.

## Automated tests and call-count checks

Before editing, the targeted baseline command passed: 52 tests in 1.92 s.

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q \
  tests/test_dictation.py tests/test_transcriber.py tests/test_pipeline.py \
  tests/test_recorder.py tests/test_assistant_privacy.py \
  tests/test_llm_manager.py tests/test_clipboard.py
```

The final full-suite result is recorded below after integration. Focused tests
assert that exact reset and numbered pending choices start no model; file search
uses one assistant request instead of a second synthesis request; multiple,
invalid or truncated calls produce no side effect; cancellation before the
injection transition suppresses output; a cancellation after that transition
reports that insertion has started. An offscreen Qt test covers the preview's
explicit insert flow. These are code-level checks, not desktop paste evidence.

## Assistant intent results

| Set | Baseline correct / total | Rework correct / total | Notes |
| --- | ---: | ---: | --- |
| 18 tuning cases, 3 repetitions | 42/54 | 54/54 | The old runner observed website routing to an app call and accepted malformed arguments. |
| 6 holdouts, 3 repetitions | 9/18 | 18/18 | Negated launch, two explicit targets and queued cancellation improved. |

The intent score does not prove target resolution or that the actual desktop
action succeeds. A safe local model round trip produced a valid `open_settings`
tool call, accepted a synthetic structured result and returned a final response
without visible reasoning text; no settings window was opened by that probe.

Warm median response times in milliseconds (three samples per case):

| Case | Baseline | Rework | Rework maximum |
| --- | ---: | ---: | ---: |
| Launch Firefox | 292 | 255 | 257 |
| Close VLC | 217 | 217 | 305 |
| Open YouTube | 267 | 246 | 343 |
| Open Downloads | 216 | 218 | 304 |
| Find invoice | 331 | 366 | 466 |
| Open settings | 245 | 259 | 339 |
| Close settings (holdout) | 220 | 244 | 246 |
| Quoted reset (holdout, no action) | 559 | 1153 | 1666 |

The quoted-reset case previously exceeded a smaller output budget in one of
three holdout runs; 512 tokens avoided that truncation, but its latency is a
material regression. File search and settings commands also regressed in this
small sample. The requirement that normal interactions be at least as fast is
therefore **not established**. Quality was preferred to lowering the token
budget after the holdout failure.

## Startup and resources

| Set | Baseline cold startup / first response | Rework cold startup / first response | Baseline / rework process-tree RSS | Baseline / rework sampled peak system VRAM |
| --- | ---: | ---: | ---: | ---: |
| Tuning | 1547 / 526 ms | 3552 / 464 ms | 443 / 440 MB | 4.49 / 4.67 GB |
| Holdout | 1543 / 456 ms | 1543 / 463 ms | 435 / 425 MB | 4.51 / 4.57 GB |

The 3552 ms startup is an outlier in this paired run and has not been explained.
Idle process-tree CPU was approximately 1–2% in one-second windows; the runner
itself contributes to this measure. Idle runner RSS was about 43.5 MB. The VRAM
numbers include the rest of the desktop, so they cannot establish a per-Vigil
regression or improvement. No new permanent daemon or indexing process was
added. Last-dictation retention keeps at most one raw and one processed 64 KiB
string for up to five minutes. Stage logs now separate STT, postprocessing,
injection dispatch, model startup, LLM response and tool execution; injection
dispatch does not verify arrival in the target application.

## Open gates

- No manual KDE Wayland target-focus, clipboard, paste or cancellation check
  has been completed. Offscreen tests cannot establish this behavior.
- No consented audio was supplied, so there is no measured STT quality or
  critical-token comparison. The paired beam-size candidate was not adopted.
- The optional model-specific sampling profile remains opt-in and unverified
  as a shipping improvement. Only the installed LFM2.5 2.6B variant was used
  for the live intent round trip; other model profiles remain unverified.
- Recording-limit recovery and optional new assistant tools remain outside
  this delivery because their adoption gates require the missing quality,
  latency and desktop evidence.

## Final integration verification

```text
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
254 passed in 4.91s
git diff --check
exit 0
```

The command used the existing virtual environment from the adjacent checkout
because this worktree had no `.venv`; its personal home path is omitted here.
The complete suite was run after moving the temporary evaluation files outside
the checkout, and again after the final code changes. The original checkout's
pre-existing `.gitignore` edit was not included in this branch.
