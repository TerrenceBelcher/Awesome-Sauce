"""Security analysis for Boot Guard, ME, and lock bits."""

import struct
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class SecurityStatus:
    """Security status of firmware."""
    boot_guard_enabled: bool = False
    boot_guard_verified: bool = False
    boot_guard_measured: bool = False
    boot_guard_policy: Optional[int] = None
    me_region_found: bool = False
    me_version: Optional[str] = None
    pfat_present: bool = False
    fd_locked: bool = False
    acm_present: bool = False
    safe_to_flash: bool = True
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class SecurityAnalyzer:
    """Analyze firmware security features."""
    
    def __init__(self, data: bytes):
        self.data = data
        self.status = SecurityStatus()
    
    def analyze(self) -> SecurityStatus:
        """Run all security checks."""
        log.info("Running security analysis...")
        
        self._check_boot_guard()
        self._check_me_region()
        self._check_pfat()
        self._check_fd_lock()
        self._determine_safety()
        
        return self.status
    
    def _check_boot_guard(self) -> None:
        """Check for Boot Guard enforcement."""
        # Look for KEYM (Boot Guard Key Manifest)
        keym_sig = b'__KEYM__'
        keym_found = self.data.find(keym_sig)
        
        if keym_found != -1:
            log.info(f"Boot Guard KEYM found at 0x{keym_found:x}")
            self.status.boot_guard_enabled = True
            
            # Parse KEYM to check policy
            if keym_found + 0x20 < len(self.data):
                # Policy is typically at offset 0x10 in KEYM
                policy_offset = keym_found + 0x10
                policy = struct.unpack('<I', self.data[policy_offset:policy_offset+4])[0]
                self.status.boot_guard_policy = policy
                
                # Bit 0: Verified boot
                # Bit 1: Measured boot
                if policy & 0x01:
                    self.status.boot_guard_verified = True
                    self.status.warnings.append("CRITICAL: Boot Guard Verified Boot is ENABLED - flashing modified BIOS will BRICK the system!")
                if policy & 0x02:
                    self.status.boot_guard_measured = True
                    self.status.warnings.append("WARNING: Boot Guard Measured Boot is enabled")
        
        # Look for BTGP (Boot Guard Policy)
        btgp_sig = b'__BTGP__'
        if self.data.find(btgp_sig) != -1:
            log.info("Boot Guard BTGP found")
            self.status.boot_guard_enabled = True
        
        # Look for ACM (Authenticated Code Module)
        acm_sig = b'ACMR'  # ACM header signature
        acm_found = self.data.find(acm_sig)
        if acm_found != -1:
            log.info(f"ACM found at 0x{acm_found:x}")
            self.status.acm_present = True
        
        # Check for HashDXE (Boot Guard enforcement in DXE phase)
        hashdxe_patterns = [
            b'HashDxe',
            b'BootGuardDxe',
        ]
        for pattern in hashdxe_patterns:
            if pattern in self.data:
                log.warning(f"Boot Guard enforcement module found: {pattern.decode('ascii', errors='ignore')}")
                self.status.warnings.append(f"CRITICAL: Boot Guard HashDXE found - DO NOT flash modified BIOS!")
    
    def _check_me_region(self) -> None:
        """Check for Intel Management Engine region."""
        # Look for ME manifest signature
        me_sigs = [
            b'$MN2',  # ME Manifest v2
            b'$MAN',  # ME Manifest
            b'$FPT',  # Flash Partition Table
        ]
        
        for sig in me_sigs:
            pos = self.data.find(sig)
            if pos != -1:
                log.info(f"ME region signature {sig} found at 0x{pos:x}")
                self.status.me_region_found = True
                
                # Try to parse version
                if sig == b'$MN2' and pos + 0x20 < len(self.data):
                    try:
                        # Version is typically at offset 0x18
                        ver_offset = pos + 0x18
                        major = struct.unpack('<H', self.data[ver_offset:ver_offset+2])[0]
                        minor = struct.unpack('<H', self.data[ver_offset+2:ver_offset+4])[0]
                        hotfix = struct.unpack('<H', self.data[ver_offset+4:ver_offset+6])[0]
                        build = struct.unpack('<H', self.data[ver_offset+6:ver_offset+8])[0]
                        self.status.me_version = f"{major}.{minor}.{hotfix}.{build}"
                        log.info(f"ME version: {self.status.me_version}")
                    except:
                        pass
                
                break
    
    def _check_pfat(self) -> None:
        """Check for PFAT (Platform Flash Armoring Technology)."""
        # PFAT signature
        pfat_sig = b'_PFAT_'
        pfat_found = self.data.find(pfat_sig)
        
        if pfat_found != -1:
            log.warning(f"PFAT found at 0x{pfat_found:x}")
            self.status.pfat_present = True
            self.status.warnings.append("CRITICAL: PFAT is present - flashing may fail or brick system!")
    
    def _check_fd_lock(self) -> None:
        """Check for Flash Descriptor lock."""
        # Flash Descriptor starts with signature 0x0FF0A55A
        fd_sig = struct.pack('<I', 0x0FF0A55A)
        fd_pos = self.data.find(fd_sig)
        
        if fd_pos != -1:
            log.info(f"Flash Descriptor found at 0x{fd_pos:x}")
            
            # Check FLMSTR registers (typically at offset 0x80 in FD)
            if fd_pos + 0x100 < len(self.data):
                flmstr1 = struct.unpack('<I', self.data[fd_pos+0x80:fd_pos+0x84])[0]
                
                # Check if write access is locked (heuristic)
                if flmstr1 & 0x0FFF != 0x0FFF:
                    log.warning("Flash Descriptor appears locked")
                    self.status.fd_locked = True
                    self.status.warnings.append("WARNING: Flash Descriptor may be locked - external programmer may be required")
    
    def _determine_safety(self) -> None:
        """Determine if it's safe to flash modified firmware."""
        # Hard fail conditions
        if self.status.boot_guard_verified:
            self.status.safe_to_flash = False
            log.error("UNSAFE TO FLASH: Boot Guard Verified Boot is enabled")
        
        if self.status.pfat_present:
            self.status.safe_to_flash = False
            log.error("UNSAFE TO FLASH: PFAT is present")
        
        # Warnings but not hard fail
        if self.status.boot_guard_measured:
            log.warning("Boot Guard Measured Boot is enabled - TPM measurements may change")
        
        if self.status.fd_locked:
            log.warning("Flash Descriptor is locked - may need external programmer")
        
        if self.status.safe_to_flash:
            log.info("[OK] No critical security blocks detected - safe to flash with caution")
        else:
            log.error("[FAIL] CRITICAL security blocks detected - DO NOT FLASH!")


def extract_cpuid_from_microcode(data: bytes, offset: int) -> Optional[int]:
    """Extract CPUID from microcode update header.
    
    Microcode header format:
    0x00: Header Version (4 bytes)
    0x04: Update Revision (4 bytes)
    0x08: Date (4 bytes)
    0x0C: Processor Signature (CPUID) (4 bytes)
    0x10: Checksum (4 bytes)
    0x14: Loader Revision (4 bytes)
    0x18: Processor Flags (4 bytes)
    0x1C: Data Size (4 bytes)
    0x20: Total Size (4 bytes)
    """
    try:
        if offset + 0x30 > len(data):
            return None
        
        header = data[offset:offset+0x30]
        
        # Check header version (should be 1)
        hdr_ver = struct.unpack('<I', header[0x00:0x04])[0]
        if hdr_ver != 1:
            return None
        
        # Extract CPUID (processor signature)
        cpuid = struct.unpack('<I', header[0x0C:0x10])[0]
        
        # Validate it looks like a real CPUID (family 6 for Intel)
        family = (cpuid >> 8) & 0x0F
        if family == 6:  # Intel Core family
            return cpuid
        
        return None
    
    except Exception as e:
        log.debug(f"Error extracting CPUID from microcode: {e}")
        return None


def find_microcode_updates(data: bytes) -> List[Tuple[int, int]]:
    """Find microcode updates in firmware.
    
    Returns list of (offset, cpuid) tuples.
    """
    updates = []
    
    # Microcode updates are typically aligned to 1KB
    for offset in range(0, len(data) - 0x800, 0x400):
        # Check for microcode header signature (heuristic)
        if offset + 0x30 > len(data):
            break
        
        # Header version at offset 0
        try:
            hdr_ver = struct.unpack('<I', data[offset:offset+4])[0]
            if hdr_ver != 1:
                continue
            
            # Try to extract CPUID
            cpuid = extract_cpuid_from_microcode(data, offset)
            if cpuid:
                log.info(f"Found microcode update at 0x{offset:x}, CPUID 0x{cpuid:08X}")
                updates.append((offset, cpuid))
        except:
            continue
    
    return updates
