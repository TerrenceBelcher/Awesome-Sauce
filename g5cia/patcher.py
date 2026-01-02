"""BIOS patching operations with validation."""

import struct
import logging
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass

from .utils import (
    encode_power_limit, decode_power_limit,
    encode_voltage_offset, decode_voltage_offset,
    encode_tau, checksum8, checksum16,
    try_lzma_compress, hexdump
)
from .offsets import get_offset

log = logging.getLogger(__name__)


@dataclass
class Patch:
    """A single patch operation."""
    offset: int
    old_data: bytes
    new_data: bytes
    description: str
    applied: bool = False


class Patcher:
    """BIOS patcher with validation and logging."""
    
    def __init__(self, data: bytes):
        self.data = bytearray(data)
        self.patches: List[Patch] = []
        self.setup_base: Optional[int] = None
    
    def set_setup_base(self, offset: int) -> None:
        """Set base offset for Setup variable."""
        self.setup_base = offset
        log.info(f"Setup base set to 0x{offset:x}")
    
    def patch_byte(self, offset: int, value: int, description: str = "") -> bool:
        """Patch a single byte."""
        if offset >= len(self.data):
            log.error(f"Offset 0x{offset:x} beyond image size")
            return False
        
        old_val = self.data[offset]
        if old_val == value:
            log.debug(f"Byte at 0x{offset:x} already {value:02X}")
            return True
        
        patch = Patch(
            offset=offset,
            old_data=bytes([old_val]),
            new_data=bytes([value]),
            description=description or f"Patch byte at 0x{offset:x}"
        )
        
        self._check_overlap(patch)
        self.patches.append(patch)
        self.data[offset] = value
        patch.applied = True
        
        log.info(f"Patched 0x{offset:x}: 0x{old_val:02X} -> 0x{value:02X} ({description})")
        return True
    
    def patch_word(self, offset: int, value: int, description: str = "") -> bool:
        """Patch a 16-bit word (little-endian)."""
        if offset + 2 > len(self.data):
            log.error(f"Offset 0x{offset:x} beyond image size")
            return False
        
        old_data = self.data[offset:offset+2]
        new_data = struct.pack('<H', value & 0xFFFF)
        
        if old_data == new_data:
            log.debug(f"Word at 0x{offset:x} already {value:04X}")
            return True
        
        patch = Patch(
            offset=offset,
            old_data=bytes(old_data),
            new_data=new_data,
            description=description or f"Patch word at 0x{offset:x}"
        )
        
        self._check_overlap(patch)
        self.patches.append(patch)
        self.data[offset:offset+2] = new_data
        patch.applied = True
        
        log.info(f"Patched 0x{offset:x}: 0x{old_data.hex()} -> 0x{new_data.hex()} ({description})")
        return True
    
    def patch_bytes(self, offset: int, data: bytes, description: str = "") -> bool:
        """Patch multiple bytes."""
        if offset + len(data) > len(self.data):
            log.error(f"Patch at 0x{offset:x} would exceed image size")
            return False
        
        old_data = self.data[offset:offset+len(data)]
        
        if old_data == data:
            log.debug(f"Bytes at 0x{offset:x} already match")
            return True
        
        patch = Patch(
            offset=offset,
            old_data=bytes(old_data),
            new_data=data,
            description=description or f"Patch {len(data)} bytes at 0x{offset:x}"
        )
        
        self._check_overlap(patch)
        self.patches.append(patch)
        self.data[offset:offset+len(data)] = data
        patch.applied = True
        
        log.info(f"Patched 0x{offset:x} ({len(data)} bytes): {description}")
        return True
    
    def _check_overlap(self, patch: Patch) -> None:
        """Check if patch overlaps with existing patches."""
        for existing in self.patches:
            if not existing.applied:
                continue
            
            # Check if ranges overlap
            if (patch.offset < existing.offset + len(existing.new_data) and
                patch.offset + len(patch.new_data) > existing.offset):
                log.warning(f"Patch overlap detected: {patch.description} overlaps with {existing.description}")
    
    def patch_setup_offset(self, name: str, value: int) -> bool:
        """Patch a Setup variable by name using offset map."""
        if self.setup_base is None:
            log.error("Setup base not set - cannot patch Setup offsets")
            return False
        
        offset, size = get_offset(name)
        abs_offset = self.setup_base + offset
        
        from .offsets import get_description
        desc = get_description(name)
        
        if size == 1:
            return self.patch_byte(abs_offset, value, f"{name}: {desc}")
        elif size == 2:
            return self.patch_word(abs_offset, value, f"{name}: {desc}")
        else:
            log.error(f"Unsupported size {size} for offset {name}")
            return False
    
    def set_power_limit(self, name: str, watts: int) -> bool:
        """Set power limit in watts."""
        # Power limits are stored as 2 bytes (L and H)
        encoded = encode_power_limit(watts)
        
        # Patch low and high bytes
        low_name = name + 'L'
        high_name = name + 'H'
        
        success = True
        success &= self.patch_setup_offset(low_name, encoded[0])
        success &= self.patch_setup_offset(high_name, encoded[1])
        
        if success:
            log.info(f"Set {name} to {watts}W")
        
        return success
    
    def set_voltage_offset(self, name_prefix: str, mv: int) -> bool:
        """Set voltage offset in mV (negative = undervolt)."""
        encoded = encode_voltage_offset(mv)
        
        # Patch low and high bytes
        low_name = name_prefix + 'OL'
        high_name = name_prefix + 'OH'
        
        success = True
        success &= self.patch_setup_offset(low_name, encoded[0])
        success &= self.patch_setup_offset(high_name, encoded[1])
        
        if success:
            log.info(f"Set {name_prefix} offset to {mv}mV")
        
        return success
    
    def unlock_all(self) -> bool:
        """Unlock all common lock bits."""
        locks = ['CfgLk', 'OcLk', 'PlLk', 'BiosLk', 'PkgLk', 'TdpLk']
        success = True
        
        for lock in locks:
            success &= self.patch_setup_offset(lock, 0)
        
        return success
    
    def set_hap_bit(self, enable: bool, pch_offset: int = 0x3454) -> bool:
        """Set HAP (High Assurance Platform) bit to disable ME.
        
        Args:
            enable: True to disable ME, False to enable
            pch_offset: PCH strap offset (platform-specific)
        """
        # HAP bit is in PCH straps, not Setup
        # This is a direct firmware patch
        
        if pch_offset + 4 > len(self.data):
            log.error("PCH strap offset beyond image")
            return False
        
        # Read current value
        current = struct.unpack('<I', self.data[pch_offset:pch_offset+4])[0]
        
        # HAP bit is typically bit 16
        if enable:
            new_val = current | (1 << 16)
        else:
            new_val = current & ~(1 << 16)
        
        if current == new_val:
            log.info(f"HAP bit already {'set' if enable else 'cleared'}")
            return True
        
        self.patch_bytes(
            pch_offset,
            struct.pack('<I', new_val),
            f"{'Enable' if enable else 'Disable'} HAP bit (ME disable)"
        )
        
        # Read back to verify
        verify = struct.unpack('<I', self.data[pch_offset:pch_offset+4])[0]
        if verify != new_val:
            log.error("HAP bit read-back verification failed!")
            return False
        
        log.info(f"HAP bit {'enabled' if enable else 'disabled'} and verified")
        return True
    
    def inject_microcode(self, ucode_data: bytes, cpuid: int, inject_offset: int) -> bool:
        """Inject microcode update with full validation.
        
        Args:
            ucode_data: Complete microcode update binary
            cpuid: Expected CPUID for validation
            inject_offset: Offset to inject at
        """
        # Validate microcode header
        if len(ucode_data) < 0x30:
            log.error("Microcode data too small")
            return False
        
        # Parse header
        hdr_ver = struct.unpack('<I', ucode_data[0:4])[0]
        update_rev = struct.unpack('<I', ucode_data[4:8])[0]
        date = struct.unpack('<I', ucode_data[8:12])[0]
        proc_sig = struct.unpack('<I', ucode_data[12:16])[0]
        checksum = struct.unpack('<I', ucode_data[16:20])[0]
        total_size = struct.unpack('<I', ucode_data[32:36])[0]
        
        # Validate
        if hdr_ver != 1:
            log.error(f"Invalid microcode header version: {hdr_ver}")
            return False
        
        if proc_sig != cpuid:
            log.error(f"CPUID mismatch: expected 0x{cpuid:08X}, got 0x{proc_sig:08X}")
            return False
        
        if len(ucode_data) != total_size:
            log.error(f"Size mismatch: expected {total_size}, got {len(ucode_data)}")
            return False
        
        # Validate checksum (simple sum of all DWORDs should be 0)
        dwords = len(ucode_data) // 4
        total = sum(struct.unpack('<I', ucode_data[i:i+4])[0] for i in range(0, dwords * 4, 4))
        if total & 0xFFFFFFFF != 0:
            log.warning(f"Microcode checksum validation failed (sum: 0x{total:08X})")
        
        log.info(f"Injecting microcode: CPUID 0x{proc_sig:08X}, rev {update_rev}, date {date:08X}")
        
        # Inject
        return self.patch_bytes(inject_offset, ucode_data, f"Microcode update (CPUID 0x{proc_sig:08X})")
    
    def recalc_fv_checksum(self, fv_offset: int) -> bool:
        """Recalculate firmware volume header checksum."""
        if fv_offset + 0x38 > len(self.data):
            log.error("FV header beyond image")
            return False
        
        # Zero out existing checksum (at offset 0x32)
        self.data[fv_offset + 0x32:fv_offset + 0x34] = b'\x00\x00'
        
        # Calculate new checksum
        header = self.data[fv_offset:fv_offset+0x38]
        new_checksum = checksum16(header)
        
        # Write new checksum
        self.data[fv_offset + 0x32:fv_offset + 0x34] = struct.pack('<H', new_checksum)
        
        log.info(f"Recalculated FV checksum at 0x{fv_offset:x}: 0x{new_checksum:04X}")
        return True
    
    def get_patch_summary(self) -> str:
        """Get summary of all patches."""
        lines = [f"\n{'='*70}"]
        lines.append("PATCH SUMMARY")
        lines.append(f"{'='*70}")
        lines.append(f"Total patches: {len(self.patches)}")
        lines.append("")
        
        for i, patch in enumerate(self.patches, 1):
            lines.append(f"{i}. {patch.description}")
            lines.append(f"   Offset: 0x{patch.offset:08X}")
            lines.append(f"   Before: {patch.old_data.hex().upper()}")
            lines.append(f"   After:  {patch.new_data.hex().upper()}")
            lines.append(f"   Applied: {'✓' if patch.applied else '✗'}")
            lines.append("")
        
        lines.append(f"{'='*70}\n")
        return '\n'.join(lines)
    
    def get_data(self) -> bytes:
        """Get patched data."""
        return bytes(self.data)
