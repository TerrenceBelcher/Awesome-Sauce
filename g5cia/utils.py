"""Utility functions for compression, checksums, and encoding."""

import struct
import zlib
import logging
from typing import Optional

log = logging.getLogger(__name__)


def crc32(data: bytes) -> int:
    """Calculate CRC32 checksum."""
    return zlib.crc32(data) & 0xFFFFFFFF


def checksum8(data: bytes) -> int:
    """Calculate 8-bit checksum."""
    return sum(data) & 0xFF


def checksum16(data: bytes) -> int:
    """Calculate 16-bit checksum."""
    total = sum(struct.unpack(f'<{len(data)//2}H', data[:len(data)&~1]))
    return (0x10000 - (total & 0xFFFF)) & 0xFFFF


def try_lzma_decompress(data: bytes) -> Optional[bytes]:
    """Attempt LZMA decompression with error handling."""
    try:
        import lzma
        return lzma.decompress(data)
    except Exception as e:
        log.debug(f"LZMA decompress failed: {e}")
        return None


def try_lzma_compress(data: bytes) -> Optional[bytes]:
    """Attempt LZMA compression with error handling."""
    try:
        import lzma
        return lzma.compress(data, format=lzma.FORMAT_ALONE, 
                           filters=[{"id": lzma.FILTER_LZMA1}])
    except Exception as e:
        log.error(f"LZMA compress failed: {e}")
        return None


def try_zlib_decompress(data: bytes) -> Optional[bytes]:
    """Attempt zlib decompression with error handling."""
    try:
        return zlib.decompress(data)
    except Exception as e:
        log.debug(f"Zlib decompress failed: {e}")
        return None


def encode_power_limit(watts: int) -> bytes:
    """Encode power limit in watts to firmware format (milliwatts * 8)."""
    mw = watts * 1000
    encoded = mw * 8
    return struct.pack('<H', encoded & 0xFFFF)


def decode_power_limit(data: bytes) -> int:
    """Decode power limit from firmware format to watts."""
    encoded = struct.unpack('<H', data)[0]
    mw = encoded // 8
    return mw // 1000


def encode_voltage_offset(mv: int) -> bytes:
    """Encode voltage offset in mV to firmware format (signed, 1/1024V units).
    
    Negative offsets = undervolt.
    Formula: raw = (mV / 1000) * 1024 = mV * 1.024
    """
    # Convert mV to raw units (1/1024V)
    raw = int(mv * 1.024)
    # Pack as signed 16-bit (clamp to valid range)
    raw = max(-32768, min(32767, raw))
    return struct.pack('<h', raw)


def decode_voltage_offset(data: bytes) -> int:
    """Decode voltage offset from firmware format to mV."""
    raw = struct.unpack('<h', data)[0]
    # Convert from 1/1024V units to mV
    return int(raw / 1.024)


def encode_tau(seconds: int) -> bytes:
    """Encode Tau (turbo time window) in seconds to firmware format."""
    # Tau is stored as power-of-2 multiplier and mantissa
    # Simple encoding: store seconds directly for small values
    return struct.pack('<B', min(seconds, 255))


def hexdump(data: bytes, width: int = 16) -> str:
    """Create hex dump string of binary data."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        lines.append(f"{i:04X}: {hex_str}")
    return '\n'.join(lines)


def align_up(value: int, alignment: int) -> int:
    """Align value up to alignment boundary."""
    return (value + alignment - 1) & ~(alignment - 1)


def guid_to_str(guid_bytes: bytes) -> str:
    """Convert 16-byte GUID to string format."""
    if len(guid_bytes) != 16:
        return "INVALID-GUID"
    
    d1, d2, d3 = struct.unpack('<IHH', guid_bytes[:8])
    d4 = guid_bytes[8:10]
    d5 = guid_bytes[10:16]
    
    return f"{d1:08X}-{d2:04X}-{d3:04X}-{d4.hex().upper()}-{d5.hex().upper()}"


def str_to_guid(guid_str: str) -> bytes:
    """Convert GUID string to 16-byte format."""
    parts = guid_str.split('-')
    if len(parts) != 5:
        raise ValueError("Invalid GUID format")
    
    d1 = struct.pack('<I', int(parts[0], 16))
    d2 = struct.pack('<H', int(parts[1], 16))
    d3 = struct.pack('<H', int(parts[2], 16))
    d4 = bytes.fromhex(parts[3])
    d5 = bytes.fromhex(parts[4])
    
    return d1 + d2 + d3 + d4 + d5
