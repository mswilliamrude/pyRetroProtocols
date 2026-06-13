# Archive

Files moved here during the 2026-06-13 repository cleanup. Preserved for reference;
not part of the active codebase.

---

## session_artifacts/

Files from development sessions — logs, handoff docs, and debugging captures.

| File | What it is |
|------|-----------|
| `SESSION_HANDOVER.md` | End-of-session summary from May 31: documents the Bastion proxy evasion breakthrough (Quoted-Printable `--zdle 23` + UTF-8 encoder bypass). Superseded by `rzsz/STATUS.md`. |
| `session_receipt.jsonl` | Multi-agent dispatch receipt from June 3 (3x gpt-4o-mini subagents, ~20k tokens, $0 cost). Documents the Skill_Multiagent council experiment run against this repo. |
| `session_wal.jsonl` | Write-ahead log from the same multi-agent session. Raw message stream. |
| `sse_curl.log` | Raw SSE (Server-Sent Events) curl capture — debugging the MCP/Unimind event stream connection. |
| `sse_raw.txt` | Same SSE debugging, different capture format. |
| `runme_notes.md` | Azure VNet container deployment guide (ACR + ACI into private VNet). Likely from testing `szaio.py` inside a container deployed to Azure. |

---

## debug_tests/

Iterative debugging scripts created while chasing specific bugs. Each numbered file
is a variation on the "first" version (e.g., `test_crc.py` is the keeper; `test_crc2-5.py`
are iterations trying different approaches to the same problem).

| File | What it was debugging |
|------|----------------------|
| `test_crc2.py` — `test_crc5.py` | CRC calculation iterations — chasing a mismatch between Python CRC and `lrzsz` peer CRC. |
| `test_crc_compare.py` | Side-by-side CRC output comparison between our implementation and reference. |
| `test_crc_zfile2.py`, `test_crc_zfile3.py` | CRC validation specifically on ZFILE headers (filename/metadata frame). |
| `test_crc_zfile_dropped_s.py` | Debugging a dropped 's' character in ZFILE header CRC — the Bastion was eating it. |
| `test_printable_zdle2.py` — `test_printable_zdle5.py` | Iterations on Quoted-Printable ZDLE encoding to evade Bastion control-character stripping. |
| `test_zdle_printable.py` | Earlier attempt at the same ZDLE printable encoding problem. |
| `test_zdle.txt` | Raw ZDLE byte sequences for manual inspection. |
| `test_log_sz.py` | Logging wrapper around sz to capture raw byte output for debugging. |
| `test_match.py` | Pattern matching tests for ZMODEM header recognition. |
| `test_re.py` | Regex experiments for parsing ZMODEM hex headers. |
| `test_rx.py` | Standalone receiver test (manual, not pytest). |
| `test_stream.py` | Raw stream handling test — diagnosing byte-level framing issues. |
| `test_stripping.py` | Testing which bytes the Bastion proxy strips (control chars, high-bit, etc.). |
| `test_utf8.py` | UTF-8 encoding validation — ensuring our encoder produces valid sequences. |
| `test_pyz_origin.py` | Test against the original `pyZMODEM` library (upstream comparison). |

---

## misc/

One-off utilities and files that don't belong in this repo or have no ongoing purpose.

| File | What it is |
|------|-----------|
| `dgdg.py` | DuckDuckGo CLI scraper. Doesn't belong here — canonical copy lives at `~/git/bash_environment/scripts/dgdg.py`. |
| `szaio_wrapper.py` | Subprocess wrapper that launches `szaio.py` with `--zdle 23 --debug` and logs reads to `/tmp/szaio_read.log`. One-off debugging harness. |
| `test_mcp.py` | SSE client connecting to an MCP/Unimind endpoint. Testing multi-agent integration, not protocol code. |
| `test_tools.py` | Same as above — SSE event stream test client. Not related to ZMODEM/HS/Link. |
| `uuencode_sed` | One-liner: `cat /tmp/data | sed | openssl base64 -d | zcat > /usr/local/bin/sz.py`. Quick deployment trick to transfer `sz.py` through a restricted shell via uuencoding. |
| `dummy_file.txt`, `dummy_file2.txt` | Empty/trivial test payloads used during manual transfer testing. |
| `request_output.txt` | Captured output from a test transfer — raw bytes for inspection. |

---

## When to look here

- **Debugging a CRC issue?** Check `debug_tests/test_crc*.py` for prior approaches.
- **Bastion evasion broke?** Check `debug_tests/test_printable_zdle*.py` and `debug_tests/test_stripping.py` for what was tried.
- **Need the Azure container deployment steps?** See `session_artifacts/runme_notes.md`.
- **Wondering how the multi-agent experiment went?** See `session_artifacts/session_receipt.jsonl`.
