"""ACPI table extraction and patching."""

import struct
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class ACPITable:
    """ACPI table information."""
    signature: str
    offset: int
    length: int
    revision: int
    oem_id: str
    oem_table_id: str
    oem_revision: int
    creator_id: str
    creator_revision: int


@dataclass
class ACPIPatch:
    """ACPI binary patch."""
    search: bytes
    replace: bytes
    description: str
    count: int = -1  # -1 = all occurrences, >0 = limit


class ACPIPatcher:
    """Extract and patch ACPI tables."""
    
    # ACPI table signature
    RSDP_SIGNATURE = b'RSD PTR '
    
    def __init__(self, bios_data: bytes):
        """Initialize with BIOS data.
        
        Args:
            bios_data: Raw BIOS firmware data
        """
        self.bios_data = bytearray(bios_data)
        self.tables: Dict[str, List[ACPITable]] = {}
        self.rsdp_offset: Optional[int] = None
        
    def list_tables(self) -> List[ACPITable]:
        """Find and list all ACPI tables.
        
        Returns:
            List of ACPITable objects
        """
        all_tables = []
        
        # Find RSDP (Root System Description Pointer)
        self.rsdp_offset = self._find_rsdp()
        
        if not self.rsdp_offset:
            log.warning("RSDP not found - ACPI tables may not be accessible")
            return []
        
        log.debug(f"Found RSDP at 0x{self.rsdp_offset:x}")
        
        # Parse RSDT/XSDT to find table pointers
        tables_offsets = self._parse_rsdp(self.rsdp_offset)
        
        # Parse each table
        for offset in tables_offsets:
            try:
                table = self._parse_table_header(offset)
                if table:
                    sig = table.signature
                    if sig not in self.tables:
                        self.tables[sig] = []
                    
                    self.tables[sig].append(table)
                    all_tables.append(table)
                    
                    log.debug(f"Found {sig} table at 0x{offset:x} ({table.length} bytes)")
            except Exception as e:
                log.debug(f"Error parsing table at 0x{offset:x}: {e}")
        
        log.info(f"Found {len(all_tables)} ACPI tables")
        return all_tables
    
    def _find_rsdp(self) -> Optional[int]:
        """Find RSDP in BIOS data.
        
        Returns:
            RSDP offset or None
        """
        # RSDP is typically in:
        # 1. First 1KB of EBDA (Extended BIOS Data Area)
        # 2. 0xE0000-0xFFFFF range (legacy)
        
        # Search in common locations within BIOS image
        search_ranges = [
            (0, min(0x100000, len(self.bios_data))),  # First 1MB
        ]
        
        for start, end in search_ranges:
            pos = start
            while pos < end - 8:
                if self.bios_data[pos:pos + 8] == self.RSDP_SIGNATURE:
                    # Verify checksum
                    if self._verify_rsdp_checksum(pos):
                        return pos
                
                pos += 16  # RSDP is 16-byte aligned
        
        return None
    
    def _verify_rsdp_checksum(self, offset: int) -> bool:
        """Verify RSDP checksum.
        
        Args:
            offset: RSDP offset
            
        Returns:
            True if valid
        """
        if offset + 20 > len(self.bios_data):
            return False
        
        # RSDP 1.0 is 20 bytes
        rsdp_data = self.bios_data[offset:offset + 20]
        
        checksum = sum(rsdp_data) & 0xFF
        return checksum == 0
    
    def _parse_rsdp(self, offset: int) -> List[int]:
        """Parse RSDP to get table pointers.
        
        Args:
            offset: RSDP offset
            
        Returns:
            List of table offsets
        """
        tables = []
        
        if offset + 20 > len(self.bios_data):
            return tables
        
        # Read RSDT pointer (offset 16-19 in RSDP 1.0)
        rsdt_ptr = struct.unpack('<I', self.bios_data[offset + 16:offset + 20])[0]
        
        # For simplicity, search for table signatures directly
        # A full implementation would parse RSDT/XSDT pointer arrays
        
        # Common ACPI table signatures
        signatures = [
            b'DSDT', b'SSDT', b'FADT', b'MADT', b'MCFG',
            b'HPET', b'WAET', b'BGRT', b'FPDT', b'DMAR',
        ]
        
        for sig in signatures:
            pos = 0
            while pos < len(self.bios_data) - 4:
                if self.bios_data[pos:pos + 4] == sig:
                    # Verify it looks like a valid ACPI table
                    if self._is_valid_table_header(pos):
                        tables.append(pos)
                        pos += 36  # Skip this table's header
                        continue
                
                pos += 1
        
        return tables
    
    def _is_valid_table_header(self, offset: int) -> bool:
        """Check if offset points to valid ACPI table header.
        
        Args:
            offset: Potential table offset
            
        Returns:
            True if looks valid
        """
        if offset + 36 > len(self.bios_data):
            return False
        
        # Read length field (offset 4-7)
        length = struct.unpack('<I', self.bios_data[offset + 4:offset + 8])[0]
        
        # Sanity check
        if length < 36 or length > 1024 * 1024:  # Min 36 bytes, max 1MB
            return False
        
        if offset + length > len(self.bios_data):
            return False
        
        return True
    
    def _parse_table_header(self, offset: int) -> Optional[ACPITable]:
        """Parse ACPI table header.
        
        Args:
            offset: Table offset
            
        Returns:
            ACPITable or None
        """
        if offset + 36 > len(self.bios_data):
            return None
        
        # ACPI table header format:
        # 0-3: Signature
        # 4-7: Length
        # 8: Revision
        # 9: Checksum
        # 10-15: OEM ID
        # 16-23: OEM Table ID
        # 24-27: OEM Revision
        # 28-31: Creator ID
        # 32-35: Creator Revision
        
        signature = self.bios_data[offset:offset + 4].decode('ascii', errors='ignore')
        length = struct.unpack('<I', self.bios_data[offset + 4:offset + 8])[0]
        revision = self.bios_data[offset + 8]
        oem_id = self.bios_data[offset + 10:offset + 16].decode('ascii', errors='ignore').strip('\x00')
        oem_table_id = self.bios_data[offset + 16:offset + 24].decode('ascii', errors='ignore').strip('\x00')
        oem_revision = struct.unpack('<I', self.bios_data[offset + 24:offset + 28])[0]
        creator_id = self.bios_data[offset + 28:offset + 32].decode('ascii', errors='ignore').strip('\x00')
        creator_revision = struct.unpack('<I', self.bios_data[offset + 32:offset + 36])[0]
        
        return ACPITable(
            signature=signature,
            offset=offset,
            length=length,
            revision=revision,
            oem_id=oem_id,
            oem_table_id=oem_table_id,
            oem_revision=oem_revision,
            creator_id=creator_id,
            creator_revision=creator_revision
        )
    
    def extract_table(self, signature: str, output_path: Path, index: int = 0) -> bool:
        """Extract ACPI table to file.
        
        Args:
            signature: Table signature (e.g., 'DSDT', 'SSDT')
            output_path: Output file path
            index: Table index if multiple exist (default: 0)
            
        Returns:
            True if successful
        """
        if signature not in self.tables:
            log.error(f"Table {signature} not found")
            return False
        
        tables = self.tables[signature]
        
        if index >= len(tables):
            log.error(f"Table {signature} index {index} out of range (found {len(tables)})")
            return False
        
        table = tables[index]
        
        try:
            table_data = bytes(self.bios_data[table.offset:table.offset + table.length])
            output_path.write_bytes(table_data)
            log.info(f"Extracted {signature} table to {output_path} ({table.length} bytes)")
            return True
        except Exception as e:
            log.error(f"Failed to extract table: {e}")
            return False
    
    def patch_table(self, signature: str, patches: List[ACPIPatch], index: int = 0) -> bool:
        """Apply binary patches to ACPI table.
        
        Args:
            signature: Table signature
            patches: List of patches to apply
            index: Table index if multiple exist
            
        Returns:
            True if any patches applied
        """
        if signature not in self.tables:
            log.error(f"Table {signature} not found")
            return False
        
        tables = self.tables[signature]
        
        if index >= len(tables):
            log.error(f"Table {signature} index {index} out of range")
            return False
        
        table = tables[index]
        table_start = table.offset
        table_end = table.offset + table.length
        
        any_applied = False
        
        for patch in patches:
            applied_count = 0
            pos = table_start
            
            while pos <= table_end - len(patch.search):
                if self.bios_data[pos:pos + len(patch.search)] == patch.search:
                    # Apply patch
                    if len(patch.replace) != len(patch.search):
                        log.warning(f"Patch size mismatch for '{patch.description}' - skipping")
                        break
                    
                    self.bios_data[pos:pos + len(patch.replace)] = patch.replace
                    applied_count += 1
                    any_applied = True
                    
                    log.info(f"Applied patch: {patch.description} at 0x{pos:x}")
                    
                    # Check count limit
                    if patch.count > 0 and applied_count >= patch.count:
                        break
                    
                    pos += len(patch.search)
                else:
                    pos += 1
            
            if applied_count == 0:
                log.warning(f"Patch not applied: {patch.description} (pattern not found)")
        
        # Recalculate table checksum
        if any_applied:
            self._recalculate_checksum(table)
        
        return any_applied
    
    def inject_ssdt(self, ssdt_data: bytes) -> bool:
        """Inject a new SSDT table.
        
        Note: This is a simplified implementation. Real injection would need
        to update RSDT/XSDT pointer arrays.
        
        Args:
            ssdt_data: SSDT table data
            
        Returns:
            True if successful
        """
        # Verify it's a valid SSDT
        if len(ssdt_data) < 36:
            log.error("Invalid SSDT data (too small)")
            return False
        
        sig = ssdt_data[0:4]
        if sig != b'SSDT':
            log.error(f"Invalid SSDT signature: {sig}")
            return False
        
        # Find free space in BIOS (filled with 0xFF or 0x00)
        # This is a simplified approach - real implementation would be more sophisticated
        required_size = len(ssdt_data)
        
        pos = self._find_free_space(required_size)
        
        if not pos:
            log.error("No free space found for SSDT injection")
            return False
        
        # Write SSDT
        self.bios_data[pos:pos + len(ssdt_data)] = ssdt_data
        
        log.info(f"Injected SSDT at 0x{pos:x} ({len(ssdt_data)} bytes)")
        log.warning("[WARN] RSDT/XSDT not updated - manual pointer update required")
        
        return True
    
    def _find_free_space(self, size: int) -> Optional[int]:
        """Find free space in BIOS data.
        
        Args:
            size: Required size
            
        Returns:
            Offset or None
        """
        # Look for contiguous 0xFF or 0x00 blocks
        pos = 0
        
        while pos < len(self.bios_data) - size:
            # Check if this region is free (all 0xFF or all 0x00)
            chunk = self.bios_data[pos:pos + size]
            
            if all(b == 0xFF for b in chunk) or all(b == 0x00 for b in chunk):
                return pos
            
            pos += 4096  # Check every 4KB
        
        return None
    
    def _recalculate_checksum(self, table: ACPITable) -> None:
        """Recalculate and update table checksum.
        
        Args:
            table: ACPI table
        """
        # Checksum is at offset 9
        checksum_offset = table.offset + 9
        
        # Zero out current checksum
        self.bios_data[checksum_offset] = 0
        
        # Calculate new checksum
        table_data = self.bios_data[table.offset:table.offset + table.length]
        checksum = (256 - (sum(table_data) & 0xFF)) & 0xFF
        
        # Write new checksum
        self.bios_data[checksum_offset] = checksum
    
    def get_modified_data(self) -> bytes:
        """Get modified BIOS data with patched tables.
        
        Returns:
            Modified BIOS data
        """
        return bytes(self.bios_data)
    
    def print_tables(self) -> None:
        """Print all found ACPI tables."""
        if not self.tables:
            print("No ACPI tables found")
            return
        
        print("\n" + "="*70)
        print("ACPI TABLES")
        print("="*70)
        
        for sig, tables in sorted(self.tables.items()):
            for i, table in enumerate(tables):
                suffix = f" (#{i+1})" if len(tables) > 1 else ""
                print(f"\n[{sig}{suffix}]")
                print(f"  OEM ID:        {table.oem_id}")
                print(f"  OEM Table ID:  {table.oem_table_id}")
                print(f"  OEM Revision:  {table.oem_revision}")
                print(f"  Creator:       {table.creator_id}")
                print(f"  Revision:      {table.revision}")
                print(f"  Offset:        0x{table.offset:08X}")
                print(f"  Length:        {table.length} bytes")
        
        print("="*70 + "\n")
