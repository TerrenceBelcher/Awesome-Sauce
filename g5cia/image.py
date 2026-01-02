"""Firmware image parsing for UEFI volumes and files."""

import struct
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass

from .utils import guid_to_str, try_lzma_decompress, checksum8, checksum16

log = logging.getLogger(__name__)

# Firmware Volume Header signature
FVH_SIGNATURE = b'_FVH'

# File types
FV_FILETYPE_RAW = 0x01
FV_FILETYPE_FREEFORM = 0x02
FV_FILETYPE_SECURITY_CORE = 0x03
FV_FILETYPE_PEI_CORE = 0x04
FV_FILETYPE_DXE_CORE = 0x05
FV_FILETYPE_PEIM = 0x06
FV_FILETYPE_DRIVER = 0x07
FV_FILETYPE_COMBINED_PEIM_DRIVER = 0x08
FV_FILETYPE_APPLICATION = 0x09
FV_FILETYPE_FFS_PAD = 0xF0

# Section types
SECTION_COMPRESSION = 0x01
SECTION_GUID_DEFINED = 0x02
SECTION_PE32 = 0x10
SECTION_PIC = 0x11
SECTION_TE = 0x12
SECTION_DXE_DEPEX = 0x13
SECTION_VERSION = 0x14
SECTION_USER_INTERFACE = 0x15
SECTION_FIRMWARE_VOLUME_IMAGE = 0x17
SECTION_RAW = 0x19

# Compression types
COMPRESS_NONE = 0x00
COMPRESS_STANDARD = 0x01  # EFI standard (zlib-like)
COMPRESS_CUSTOMIZED = 0x02

# LZMA GUID
LZMA_GUID = "EE4E5898-3914-4259-9D6E-DC7BD79403CF"


@dataclass
class FirmwareVolume:
    """Parsed firmware volume."""
    offset: int
    size: int
    guid: str
    data: bytes
    files: List['FirmwareFile'] = None
    
    def __post_init__(self):
        if self.files is None:
            self.files = []


@dataclass
class FirmwareFile:
    """Parsed firmware file."""
    offset: int
    size: int
    guid: str
    file_type: int
    data: bytes
    name: Optional[str] = None


class ImageParser:
    """UEFI firmware image parser."""
    
    def __init__(self, data: bytes):
        self.data = data
        self.volumes: List[FirmwareVolume] = []
        self.setup_data: Optional[bytes] = None
        self.setup_offset: Optional[int] = None
    
    def parse(self) -> bool:
        """Parse firmware image and find volumes."""
        log.info(f"Parsing firmware image ({len(self.data)} bytes)")
        
        # Find all firmware volumes
        self._find_volumes()
        
        if not self.volumes:
            log.error("No firmware volumes found")
            return False
        
        log.info(f"Found {len(self.volumes)} firmware volumes")
        
        # Parse files in each volume
        for vol in self.volumes:
            self._parse_volume_files(vol)
        
        # Find Setup variable storage
        self._find_setup_data()
        
        return True
    
    def _find_volumes(self) -> None:
        """Scan for firmware volume headers."""
        i = 0
        while i < len(self.data) - 0x30:
            # Look for _FVH signature
            if self.data[i:i+4] == FVH_SIGNATURE:
                vol = self._parse_volume_header(i)
                if vol:
                    self.volumes.append(vol)
                    i += vol.size
                    continue
            i += 0x10  # Align to 16 bytes
    
    def _parse_volume_header(self, offset: int) -> Optional[FirmwareVolume]:
        """Parse firmware volume header at offset."""
        try:
            if offset + 0x38 > len(self.data):
                return None
            
            header = self.data[offset:offset+0x38]
            
            # Skip ZeroVector (16 bytes)
            guid_bytes = header[0x10:0x20]
            guid = guid_to_str(guid_bytes)
            
            # Read FvLength (8 bytes at offset 0x20)
            fv_length = struct.unpack('<Q', header[0x20:0x28])[0]
            
            if offset + fv_length > len(self.data):
                log.debug(f"Volume at {offset:x} extends beyond image")
                return None
            
            vol_data = self.data[offset:offset+fv_length]
            
            log.debug(f"Found FV at 0x{offset:x}, size 0x{fv_length:x}, GUID {guid}")
            
            return FirmwareVolume(
                offset=offset,
                size=fv_length,
                guid=guid,
                data=vol_data
            )
        
        except Exception as e:
            log.debug(f"Error parsing volume at {offset:x}: {e}")
            return None
    
    def _parse_volume_files(self, vol: FirmwareVolume) -> None:
        """Parse files within a firmware volume."""
        # Files start after header (usually at offset 0x48 with extended header)
        offset = 0x48
        
        while offset < len(vol.data) - 0x18:
            # Check for valid GUID (not all zeros or all FFs)
            guid_bytes = vol.data[offset:offset+16]
            if guid_bytes == b'\x00' * 16 or guid_bytes == b'\xff' * 16:
                break
            
            file = self._parse_file(vol.data, offset)
            if file:
                file.offset += vol.offset  # Absolute offset
                vol.files.append(file)
                # Align to 8 bytes
                offset += file.size
                offset = (offset + 7) & ~7
            else:
                break
    
    def _parse_file(self, data: bytes, offset: int) -> Optional[FirmwareFile]:
        """Parse firmware file at offset."""
        try:
            if offset + 0x18 > len(data):
                return None
            
            header = data[offset:offset+0x18]
            
            guid_bytes = header[0:16]
            guid = guid_to_str(guid_bytes)
            
            # Header checksum at 0x10
            hdr_checksum = header[0x10]
            
            # File type at 0x12
            file_type = header[0x12]
            
            # File size (3 bytes at 0x14)
            size_bytes = header[0x14:0x17] + b'\x00'
            file_size = struct.unpack('<I', size_bytes)[0]
            
            if file_size < 0x18 or offset + file_size > len(data):
                return None
            
            file_data = data[offset:offset+file_size]
            
            return FirmwareFile(
                offset=offset,
                size=file_size,
                guid=guid,
                file_type=file_type,
                data=file_data
            )
        
        except Exception as e:
            log.debug(f"Error parsing file at {offset:x}: {e}")
            return None
    
    def _find_setup_data(self) -> None:
        """Find Setup variable storage in firmware."""
        # Setup is typically in a NVRAM FV or stored as raw data
        # Look for common Setup GUID or variable store signature
        setup_sig = b'SETUP\x00'
        
        for i in range(0, len(self.data) - len(setup_sig), 4):
            if self.data[i:i+len(setup_sig)] == setup_sig:
                log.info(f"Found Setup signature at 0x{i:x}")
                self.setup_offset = i
                # Extract ~2KB of Setup data
                self.setup_data = self.data[i:i+0x800]
                return
        
        log.warning("Setup data not found in firmware")
    
    def find_dxe_volume(self) -> Optional[FirmwareVolume]:
        """Find DXE driver volume (for ReBAR injection)."""
        for vol in self.volumes:
            # DXE volumes typically contain DRIVER type files
            driver_count = sum(1 for f in vol.files if f.file_type == FV_FILETYPE_DRIVER)
            if driver_count > 5:  # Heuristic
                log.debug(f"Found DXE volume at 0x{vol.offset:x} ({driver_count} drivers)")
                return vol
        return None
    
    def find_free_space(self, vol: FirmwareVolume, min_size: int) -> Optional[int]:
        """Find free space in volume for injection."""
        # Look for padding (0xFF) at end of volume
        for i in range(len(vol.data) - min_size, 0x48, -0x10):
            if all(b == 0xFF for b in vol.data[i:i+min_size]):
                log.debug(f"Found {min_size} bytes free at offset 0x{i:x}")
                return vol.offset + i
        return None
    
    def extract_sections(self, file: FirmwareFile) -> List[bytes]:
        """Extract and decompress sections from a file."""
        sections = []
        offset = 0x18  # Skip file header
        
        while offset < len(file.data) - 4:
            # Section size (3 bytes)
            size_bytes = file.data[offset:offset+3] + b'\x00'
            sect_size = struct.unpack('<I', size_bytes)[0]
            
            if sect_size < 4 or offset + sect_size > len(file.data):
                break
            
            sect_type = file.data[offset+3]
            sect_data = file.data[offset+4:offset+sect_size]
            
            # Handle compression
            if sect_type == SECTION_COMPRESSION:
                decompressed = self._decompress_section(sect_data)
                if decompressed:
                    sections.append(decompressed)
            elif sect_type == SECTION_GUID_DEFINED:
                decompressed = self._decompress_guid_section(sect_data)
                if decompressed:
                    sections.append(decompressed)
            else:
                sections.append(sect_data)
            
            offset += sect_size
            offset = (offset + 3) & ~3  # Align to 4
        
        return sections
    
    def _decompress_section(self, data: bytes) -> Optional[bytes]:
        """Decompress a compression section."""
        if len(data) < 5:
            return None
        
        # Uncompressed size (4 bytes)
        uncomp_size = struct.unpack('<I', data[0:4])[0]
        comp_type = data[4]
        comp_data = data[5:]
        
        if comp_type == COMPRESS_NONE:
            return comp_data
        
        # Try LZMA first, then zlib
        result = try_lzma_decompress(comp_data)
        if result:
            return result
        
        from .utils import try_zlib_decompress
        return try_zlib_decompress(comp_data)
    
    def _decompress_guid_section(self, data: bytes) -> Optional[bytes]:
        """Decompress a GUID-defined section."""
        if len(data) < 20:
            return None
        
        guid = guid_to_str(data[0:16])
        # Data offset at 16-17
        data_offset = struct.unpack('<H', data[16:18])[0]
        
        if guid == LZMA_GUID:
            comp_data = data[data_offset:]
            return try_lzma_decompress(comp_data)
        
        return None
