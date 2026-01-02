"""Option ROM management and patching."""

import struct
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class ROMInfo:
    """Option ROM metadata."""
    rom_id: str
    offset: int
    size: int
    vendor_id: int
    device_id: int
    version: str
    rom_type: str  # 'VBIOS', 'LAN', 'RAID', 'Other'
    pci_data_offset: int


@dataclass
class OptionROM:
    """Complete Option ROM with data."""
    info: ROMInfo
    data: bytes


class OptionROMManager:
    """Manage Option ROMs in BIOS image."""
    
    # Option ROM signature
    ROM_SIGNATURE = b'\x55\xAA'
    
    # PCI Data Structure signature
    PCIR_SIGNATURE = b'PCIR'
    
    def __init__(self, bios_data: bytes):
        """Initialize with BIOS data.
        
        Args:
            bios_data: Raw BIOS firmware data
        """
        self.bios_data = bytearray(bios_data)
        self.roms: List[OptionROM] = []
        
    def list_roms(self) -> List[OptionROM]:
        """Find and list all Option ROMs.
        
        Returns:
            List of OptionROM objects
        """
        self.roms = []
        pos = 0
        
        while pos < len(self.bios_data) - 2:
            # Look for ROM signature (0x55AA)
            if self.bios_data[pos:pos+2] == self.ROM_SIGNATURE:
                try:
                    rom = self._parse_rom(pos)
                    if rom:
                        self.roms.append(rom)
                        log.debug(f"Found {rom.info.rom_type} ROM at 0x{pos:x}: "
                                f"VID={rom.info.vendor_id:04x}, DID={rom.info.device_id:04x}")
                        
                        # Skip to end of this ROM
                        pos += rom.info.size
                        continue
                except Exception as e:
                    log.debug(f"Error parsing potential ROM at 0x{pos:x}: {e}")
            
            pos += 512  # ROMs are typically 512-byte aligned
        
        log.info(f"Found {len(self.roms)} Option ROMs")
        return self.roms
    
    def _parse_rom(self, offset: int) -> Optional[OptionROM]:
        """Parse Option ROM at offset.
        
        Args:
            offset: Offset in BIOS data
            
        Returns:
            OptionROM object or None if invalid
        """
        if offset + 0x1A >= len(self.bios_data):
            return None
        
        # Read ROM header
        # Offset 0x00-0x01: Signature (0x55AA)
        # Offset 0x02: ROM size in 512-byte blocks
        # Offset 0x18-0x19: PCI Data Structure pointer
        
        rom_size_blocks = self.bios_data[offset + 0x02]
        rom_size = rom_size_blocks * 512
        
        if rom_size == 0 or rom_size > 1024 * 1024:  # Max 1MB
            return None
        
        # Get PCI Data Structure offset
        pcir_offset = struct.unpack('<H', self.bios_data[offset + 0x18:offset + 0x1A])[0]
        
        if pcir_offset == 0 or offset + pcir_offset + 24 >= len(self.bios_data):
            return None
        
        # Parse PCI Data Structure
        pcir_pos = offset + pcir_offset
        
        # Check PCIR signature
        if self.bios_data[pcir_pos:pcir_pos + 4] != self.PCIR_SIGNATURE:
            return None
        
        # Read vendor/device IDs
        vendor_id = struct.unpack('<H', self.bios_data[pcir_pos + 4:pcir_pos + 6])[0]
        device_id = struct.unpack('<H', self.bios_data[pcir_pos + 6:pcir_pos + 8])[0]
        
        # Read class code to determine ROM type
        class_code = struct.unpack('<I', 
            self.bios_data[pcir_pos + 13:pcir_pos + 16] + b'\x00')[0]
        
        rom_type = self._classify_rom(class_code, vendor_id, device_id)
        
        # Generate ROM ID
        rom_id = f"{rom_type}_{vendor_id:04x}_{device_id:04x}_{offset:08x}"
        
        # Extract version (basic heuristic)
        version = "Unknown"
        try:
            # Look for version strings in first 256 bytes
            rom_header = self.bios_data[offset:offset + min(256, rom_size)]
            
            # Common version patterns
            for pattern in [b'Ver ', b'Version ', b'V']:
                idx = rom_header.find(pattern)
                if idx != -1:
                    # Extract up to 16 chars after pattern
                    ver_data = rom_header[idx:idx + 20]
                    version = ver_data.decode('ascii', errors='ignore').strip()
                    break
        except:
            pass
        
        # Create ROM info
        info = ROMInfo(
            rom_id=rom_id,
            offset=offset,
            size=rom_size,
            vendor_id=vendor_id,
            device_id=device_id,
            version=version,
            rom_type=rom_type,
            pci_data_offset=pcir_offset
        )
        
        # Extract ROM data
        rom_data = bytes(self.bios_data[offset:offset + rom_size])
        
        return OptionROM(info=info, data=rom_data)
    
    def _classify_rom(self, class_code: int, vendor_id: int, device_id: int) -> str:
        """Classify ROM type based on PCI class code.
        
        Args:
            class_code: PCI class code
            vendor_id: PCI vendor ID
            device_id: PCI device ID
            
        Returns:
            ROM type string
        """
        # PCI Base Class codes
        base_class = (class_code >> 16) & 0xFF
        
        if base_class == 0x03:  # Display controller
            return 'VBIOS'
        elif base_class == 0x02:  # Network controller
            return 'LAN'
        elif base_class == 0x01:  # Mass storage controller
            if ((class_code >> 8) & 0xFF) == 0x04:  # RAID
                return 'RAID'
            return 'Storage'
        elif base_class == 0x0C:  # Serial bus controller
            return 'USB'
        else:
            return 'Other'
    
    def extract_rom(self, rom_id: str, output_path: Path) -> bool:
        """Extract an Option ROM to file.
        
        Args:
            rom_id: ROM identifier
            output_path: Output file path
            
        Returns:
            True if successful
        """
        rom = self._find_rom_by_id(rom_id)
        
        if not rom:
            log.error(f"ROM {rom_id} not found")
            return False
        
        try:
            output_path.write_bytes(rom.data)
            log.info(f"Extracted {rom.info.rom_type} ROM to {output_path} ({len(rom.data)} bytes)")
            return True
        except Exception as e:
            log.error(f"Failed to extract ROM: {e}")
            return False
    
    def update_rom(self, rom_id: str, new_rom_data: bytes) -> bool:
        """Update an Option ROM.
        
        Args:
            rom_id: ROM identifier
            new_rom_data: New ROM data
            
        Returns:
            True if successful
        """
        rom = self._find_rom_by_id(rom_id)
        
        if not rom:
            log.error(f"ROM {rom_id} not found")
            return False
        
        # Validate new ROM
        if len(new_rom_data) < 3:
            log.error("Invalid ROM data (too small)")
            return False
        
        if new_rom_data[0:2] != self.ROM_SIGNATURE:
            log.error("Invalid ROM signature")
            return False
        
        # Size validation
        new_size_blocks = new_rom_data[2]
        new_size = new_size_blocks * 512
        
        if new_size != len(new_rom_data):
            log.warning(f"ROM size mismatch: header says {new_size}, actual {len(new_rom_data)}")
        
        if new_size > rom.info.size:
            log.error(f"New ROM ({new_size} bytes) larger than original ({rom.info.size} bytes)")
            log.error("ROM replacement would overwrite adjacent data")
            return False
        
        # Replace ROM data
        offset = rom.info.offset
        
        # Clear old ROM area
        self.bios_data[offset:offset + rom.info.size] = b'\xFF' * rom.info.size
        
        # Write new ROM
        self.bios_data[offset:offset + len(new_rom_data)] = new_rom_data
        
        # Pad with 0xFF if smaller
        if len(new_rom_data) < rom.info.size:
            pad_size = rom.info.size - len(new_rom_data)
            self.bios_data[offset + len(new_rom_data):offset + rom.info.size] = b'\xFF' * pad_size
        
        log.info(f"Updated {rom.info.rom_type} ROM at 0x{offset:x}")
        return True
    
    def get_rom_info(self, rom_id: str) -> Optional[ROMInfo]:
        """Get ROM information.
        
        Args:
            rom_id: ROM identifier
            
        Returns:
            ROMInfo or None
        """
        rom = self._find_rom_by_id(rom_id)
        return rom.info if rom else None
    
    def _find_rom_by_id(self, rom_id: str) -> Optional[OptionROM]:
        """Find ROM by ID.
        
        Args:
            rom_id: ROM identifier
            
        Returns:
            OptionROM or None
        """
        for rom in self.roms:
            if rom.info.rom_id == rom_id:
                return rom
        return None
    
    def get_modified_data(self) -> bytes:
        """Get modified BIOS data with updated ROMs.
        
        Returns:
            Modified BIOS data
        """
        return bytes(self.bios_data)
    
    def print_roms(self) -> None:
        """Print all found ROMs."""
        if not self.roms:
            print("No Option ROMs found")
            return
        
        print("\n" + "="*70)
        print("OPTION ROMS")
        print("="*70)
        
        for rom in self.roms:
            print(f"\n[{rom.info.rom_id}]")
            print(f"  Type:      {rom.info.rom_type}")
            print(f"  Vendor:    0x{rom.info.vendor_id:04X}")
            print(f"  Device:    0x{rom.info.device_id:04X}")
            print(f"  Version:   {rom.info.version}")
            print(f"  Offset:    0x{rom.info.offset:08X}")
            print(f"  Size:      {rom.info.size} bytes ({rom.info.size // 512} blocks)")
        
        print("="*70 + "\n")
