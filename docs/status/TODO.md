# PyZMODEM Future Enhancements

## Auto-Detection of Proxy Limitations
Currently, bypassing Entra ID Bastion proxies requires passing explicit flags (`-u` for UTF-8 encoding and `--zdle 23` for control character evasion). 

### 1. Auto-detect UTF-8 / Binary Dropping
- **Goal:** Eliminate the need to manually specify the `-u` / `--utf8` flag.
- **Approach:** Implement a brief pre-transfer probe. Before emitting the standard ZMODEM signature, the sender/receiver could exchange a known binary test sequence (e.g., sending `\xd0\x18` and waiting for an echo). If the sequence times out or arrives corrupted, automatically fallback to Quoted-Printable stream encoding.

### 2. Dynamically Negotiate ZDLE Byte
- **Goal:** Eliminate the need to manually pass `--zdle 23`.
- **Approach:** Standard ZMODEM uses `0x18` (CAN). During the initial `rz-request` or a new custom handshake phase, the wrapper and remote script can test standard control characters. If `0x18` is stripped by the proxy (as seen with Bastion), automatically negotiate and agree upon a safe, printable ASCII fallback (like `23` / `#`) for the session.

