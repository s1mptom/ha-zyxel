"""SMS encoding + segmentation for the Zyxel NR7302 DAL API.

Reverse-engineered from the modem's own web UI (`app.js`, component
`CellWanSmsEdit`). Validated end-to-end against a real handset:

Send = POST /cgi-bin/DAL?oid=cellwan_sms&sessionkey=<sk>&timedelay=1 with a
plaintext JSON body (over HTTPS the modem needs NO encryption). The body shape
the UI actually sends (and that delivers) is::

    {
      "SMS_Format": 0,
      "SMS_CharacterSet": "UCS2",            # or "GSM"
      "SMS_To": "447405294457",              # digits only, no '+'
      "SMS_ContentLength": <char count>,
      "SMS_TimeStamp": "",
      "SMS_Content": "<hex of the whole message>",
      "SMS_NotifyEnable": false,             # NOTE: *not* SMS_NotifyOutboxEnable
      "SMS_Content_divLen":  [<per-segment length>, ...],
      "SMS_Content_divData": ["<per-segment hex>", ...],
    }

Key gotchas that made the naive attempt silently no-op (ZCFG_SUCCESS but the
message stuck in the Outbox, never delivered):
  * divLen/divData MUST be populated — empty arrays => nothing to transmit.
  * the field is SMS_NotifyEnable, not SMS_NotifyOutboxEnable.
  * the number is digits only ('+' is stripped by the UI's sentToFilter).

We always use UCS2 (UTF-16BE) so Cyrillic / Latin / emoji all work uniformly.
Trade-off: Latin messages that would fit GSM-7 (160 chars) are capped at 70
chars/segment in UCS2 — fine for notifications; GSM-7 packing could be added
later for cheaper long Latin texts.
"""
from __future__ import annotations

import random
import re

# From the web UI: a single PDU carries 140 payload bytes; a concatenation UDH
# eats 6 of them. UCS2 = 2 bytes/char.
CONTENT_BYTES = 140
HEADER_BYTES = 6
MAX_SEGMENTS = 7

# UCS2 capacities (in UTF-16 code units).
SINGLE_MAX_UCS2 = CONTENT_BYTES // 2          # 70
SEGMENT_MAX_UCS2 = (CONTENT_BYTES - HEADER_BYTES) // 2  # 67

# The length value the UI adds for the UDH header: ceil(8*HEADER_BYTES/7) = 7.
_HEADER_LEN_UNITS = -(-8 * HEADER_BYTES // 7)  # == 7


def normalize_number(number: str) -> str:
    """Strip everything but digits — mirrors the UI's sentToFilter."""
    return re.sub(r"\D", "", number or "")


def _ucs2_units(text: str) -> list[str]:
    """Return the message as a list of UTF-16BE code units (each 4 hex chars).

    Astral chars (emoji) become a surrogate pair = two units, matching the
    JavaScript String semantics the modem expects.
    """
    raw = text.encode("utf-16-be")
    return [raw[i : i + 2].hex() for i in range(0, len(raw), 2)]


def _chunk_units(units: list[str], size: int) -> list[list[str]]:
    """Split into <= size unit chunks without breaking a surrogate pair."""
    chunks: list[list[str]] = []
    i = 0
    n = len(units)
    while i < n:
        end = min(i + size, n)
        # Don't end on a lone high surrogate (D800-DBFF): pull it to next chunk.
        if end < n:
            last = int(units[end - 1], 16)
            if 0xD800 <= last <= 0xDBFF:
                end -= 1
        chunks.append(units[i:end])
        i = end
    return chunks


def _udh(ref: int, total: int, seq: int) -> str:
    """6-byte concatenation UDH as hex (UDHL,IEI,IEDL,RN,MN,SN)."""
    return "05" "00" "03" + f"{ref & 0xFF:02x}{total & 0xFF:02x}{seq & 0xFF:02x}"


def build_payload(number: str, message: str, *, ref: int | None = None) -> dict:
    """Build the cellwan_sms POST body for `message` to `number` (UCS2).

    Raises ValueError if the message needs more than MAX_SEGMENTS segments.
    `ref` (concatenation reference, 0-255) is randomised if not given; expose it
    only for deterministic testing.
    """
    to = normalize_number(number)
    if not to:
        raise ValueError("empty destination number")

    units = _ucs2_units(message)
    full_hex = "".join(units)
    full_len = len(units)

    if full_len <= SINGLE_MAX_UCS2:
        div_len = [full_len]
        div_data = [full_hex]
    else:
        segments = _chunk_units(units, SEGMENT_MAX_UCS2)
        if len(segments) > MAX_SEGMENTS:
            raise ValueError(
                f"message too long: {len(segments)} segments > max {MAX_SEGMENTS}"
            )
        if ref is None:
            ref = random.randint(0, 255)
        total = len(segments)
        div_len = []
        div_data = []
        for idx, seg in enumerate(segments, start=1):
            seg_hex = "".join(seg)
            div_data.append(_udh(ref, total, idx) + seg_hex)
            div_len.append(_HEADER_LEN_UNITS + len(seg))

    return {
        "SMS_Format": 0,
        "SMS_CharacterSet": "UCS2",
        "SMS_To": to,
        "SMS_ContentLength": full_len,
        "SMS_TimeStamp": "",
        "SMS_Content": full_hex,
        "SMS_NotifyEnable": False,
        "SMS_Content_divLen": div_len,
        "SMS_Content_divData": div_data,
    }


# ---- inbox decoding (for optional sensors) ----------------------------------

_GSM7 = (
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ ÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)


def decode_content(content_hex: str, charset: int) -> str:
    """Decode an inbox message. charset 0 = GSM-7 packed, 2 = UCS2 (UTF-16BE)."""
    try:
        if charset == 2:
            return bytes.fromhex(content_hex).decode("utf-16-be", errors="replace")
        # GSM-7: unpack septets, then map the default alphabet.
        data = bytes.fromhex(content_hex)
        septets: list[int] = []
        carry = bits = 0
        for b in data:
            septets.append((b << bits | carry) & 0x7F)
            carry = b >> (7 - bits)
            bits += 1
            if bits == 7:
                septets.append(carry & 0x7F)
                carry = bits = 0
        return "".join(_GSM7[c] if c < len(_GSM7) else "?" for c in septets)
    except Exception:  # noqa: BLE001 - never let a bad inbox entry crash a sensor
        return ""
