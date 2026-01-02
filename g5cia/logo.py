"""Logo extraction, replacement, and generation."""

import struct
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

from .image import ImageParser, FirmwareFile, SECTION_RAW
from .utils import try_lzma_decompress, try_lzma_compress

log = logging.getLogger(__name__)

# Image format signatures
BMP_SIG = b'BM'
PNG_SIG = b'\x89PNG\r\n\x1a\n'
JPEG_SIG = b'\xff\xd8\xff'


@dataclass
class Logo:
    """Detected logo in firmware."""
    offset: int
    size: int
    format: str  # 'BMP', 'PNG', 'JPEG'
    data: bytes
    compressed: bool = False
    section_offset: Optional[int] = None


class LogoManager:
    """Manage firmware boot logos."""
    
    def __init__(self, parser: ImageParser):
        self.parser = parser
        self.logos: List[Logo] = []
    
    def scan(self) -> List[Logo]:
        """Scan firmware for logos."""
        log.info("Scanning for logos...")
        self.logos.clear()
        
        # Scan raw data
        self._scan_data(self.parser.data)
        
        # Scan decompressed sections
        for vol in self.parser.volumes:
            for file in vol.files:
                sections = self.parser.extract_sections(file)
                for sect_data in sections:
                    self._scan_data(sect_data)
        
        log.info(f"Found {len(self.logos)} logos")
        return self.logos
    
    def _scan_data(self, data: bytes) -> None:
        """Scan data for image signatures."""
        # BMP
        for i in range(0, len(data) - 2, 4):
            if data[i:i+2] == BMP_SIG:
                logo = self._parse_bmp(data, i)
                if logo:
                    self.logos.append(logo)
        
        # PNG
        for i in range(0, len(data) - 8, 4):
            if data[i:i+8] == PNG_SIG:
                logo = self._parse_png(data, i)
                if logo:
                    self.logos.append(logo)
        
        # JPEG
        for i in range(0, len(data) - 3, 4):
            if data[i:i+3] == JPEG_SIG:
                logo = self._parse_jpeg(data, i)
                if logo:
                    self.logos.append(logo)
    
    def _parse_bmp(self, data: bytes, offset: int) -> Optional[Logo]:
        """Parse BMP header to get size."""
        try:
            if offset + 14 > len(data):
                return None
            
            # File size at offset 2
            file_size = struct.unpack('<I', data[offset+2:offset+6])[0]
            
            # Sanity check
            if file_size < 54 or offset + file_size > len(data):
                return None
            
            # Extract image data
            img_data = data[offset:offset+file_size]
            
            log.debug(f"Found BMP at 0x{offset:x}, size {file_size}")
            
            return Logo(
                offset=offset,
                size=file_size,
                format='BMP',
                data=img_data
            )
        except:
            return None
    
    def _parse_png(self, data: bytes, offset: int) -> Optional[Logo]:
        """Parse PNG to find end."""
        try:
            # Find IEND chunk
            iend_sig = b'IEND'
            end_pos = data.find(iend_sig, offset)
            
            if end_pos == -1:
                return None
            
            # PNG ends 8 bytes after IEND signature (4 CRC + 0)
            file_size = end_pos - offset + 12
            
            if offset + file_size > len(data):
                return None
            
            img_data = data[offset:offset+file_size]
            
            log.debug(f"Found PNG at 0x{offset:x}, size {file_size}")
            
            return Logo(
                offset=offset,
                size=file_size,
                format='PNG',
                data=img_data
            )
        except:
            return None
    
    def _parse_jpeg(self, data: bytes, offset: int) -> Optional[Logo]:
        """Parse JPEG to find end marker."""
        try:
            # Find EOI marker (0xFF 0xD9)
            eoi_sig = b'\xff\xd9'
            end_pos = data.find(eoi_sig, offset)
            
            if end_pos == -1:
                return None
            
            file_size = end_pos - offset + 2
            
            if offset + file_size > len(data):
                return None
            
            img_data = data[offset:offset+file_size]
            
            log.debug(f"Found JPEG at 0x{offset:x}, size {file_size}")
            
            return Logo(
                offset=offset,
                size=file_size,
                format='JPEG',
                data=img_data
            )
        except:
            return None
    
    def list_logos(self) -> None:
        """Print list of detected logos."""
        print("\n" + "="*70)
        print("FIRMWARE LOGOS")
        print("="*70)
        
        if not self.logos:
            print("No logos found")
        else:
            for i, logo in enumerate(self.logos, 1):
                print(f"{i}. {logo.format} at 0x{logo.offset:08X}, {logo.size} bytes")
        
        print("="*70 + "\n")
    
    def extract(self, index: int, output_path: str) -> bool:
        """Extract logo to file.
        
        Args:
            index: Logo index (0-based)
            output_path: Output file path
        
        Returns:
            True if successful
        """
        if index < 0 or index >= len(self.logos):
            log.error(f"Invalid logo index: {index}")
            return False
        
        logo = self.logos[index]
        Path(output_path).write_bytes(logo.data)
        log.info(f"Extracted {logo.format} logo to {output_path} ({logo.size} bytes)")
        return True
    
    def replace(self, data: bytearray, index: int, new_image_path: str) -> bool:
        """Replace logo in firmware.
        
        Args:
            data: Firmware data (modified in-place)
            index: Logo index to replace
            new_image_path: Path to new image file
        
        Returns:
            True if successful
        """
        if index < 0 or index >= len(self.logos):
            log.error(f"Invalid logo index: {index}")
            return False
        
        logo = self.logos[index]
        new_data = Path(new_image_path).read_bytes()
        
        # Validate format
        new_format = self._detect_format(new_data)
        if not new_format:
            log.error("Could not detect image format")
            return False
        
        # Check size
        if len(new_data) > logo.size:
            log.error(f"New image too large: {len(new_data)} > {logo.size}")
            return False
        
        log.info(f"Replacing {logo.format} logo at 0x{logo.offset:x} with {new_format}")
        
        # Replace data
        data[logo.offset:logo.offset+len(new_data)] = new_data
        
        # Pad remaining space with 0xFF
        if len(new_data) < logo.size:
            data[logo.offset+len(new_data):logo.offset+logo.size] = b'\xff' * (logo.size - len(new_data))
        
        return True
    
    def _detect_format(self, data: bytes) -> Optional[str]:
        """Detect image format from data."""
        if data[:2] == BMP_SIG:
            return 'BMP'
        elif data[:8] == PNG_SIG:
            return 'PNG'
        elif data[:3] == JPEG_SIG:
            return 'JPEG'
        return None
    
    def generate_solid_color(self, width: int, height: int, 
                           color: Tuple[int, int, int]) -> bytes:
        """Generate solid color BMP.
        
        Args:
            width: Image width
            height: Image height
            color: RGB tuple (0-255 each)
        
        Returns:
            BMP file data
        """
        # BMP header (14 bytes) + DIB header (40 bytes) + pixel data
        row_size = (width * 3 + 3) & ~3  # 3 bytes per pixel, aligned to 4
        pixel_data_size = row_size * height
        file_size = 54 + pixel_data_size
        
        # BMP file header
        bmp = bytearray(b'BM')
        bmp += struct.pack('<I', file_size)
        bmp += struct.pack('<I', 0)  # Reserved
        bmp += struct.pack('<I', 54)  # Pixel data offset
        
        # DIB header (BITMAPINFOHEADER)
        bmp += struct.pack('<I', 40)  # Header size
        bmp += struct.pack('<i', width)
        bmp += struct.pack('<i', height)
        bmp += struct.pack('<H', 1)  # Planes
        bmp += struct.pack('<H', 24)  # Bits per pixel
        bmp += struct.pack('<I', 0)  # Compression (none)
        bmp += struct.pack('<I', pixel_data_size)
        bmp += struct.pack('<i', 2835)  # X pixels per meter
        bmp += struct.pack('<i', 2835)  # Y pixels per meter
        bmp += struct.pack('<I', 0)  # Colors in palette
        bmp += struct.pack('<I', 0)  # Important colors
        
        # Pixel data (BGR format, bottom to top)
        b, g, r = color
        row = bytes([b, g, r]) * width
        row += b'\x00' * (row_size - width * 3)  # Padding
        
        for _ in range(height):
            bmp += row
        
        log.info(f"Generated {width}x{height} solid color BMP ({color})")
        return bytes(bmp)
    
    def generate_gradient(self, width: int, height: int,
                         color1: Tuple[int, int, int],
                         color2: Tuple[int, int, int]) -> bytes:
        """Generate vertical gradient BMP.
        
        Args:
            width: Image width
            height: Image height
            color1: Top color RGB
            color2: Bottom color RGB
        
        Returns:
            BMP file data
        """
        row_size = (width * 3 + 3) & ~3
        pixel_data_size = row_size * height
        file_size = 54 + pixel_data_size
        
        # BMP file header
        bmp = bytearray(b'BM')
        bmp += struct.pack('<I', file_size)
        bmp += struct.pack('<I', 0)
        bmp += struct.pack('<I', 54)
        
        # DIB header
        bmp += struct.pack('<I', 40)
        bmp += struct.pack('<i', width)
        bmp += struct.pack('<i', height)
        bmp += struct.pack('<H', 1)
        bmp += struct.pack('<H', 24)
        bmp += struct.pack('<I', 0)
        bmp += struct.pack('<I', pixel_data_size)
        bmp += struct.pack('<i', 2835)
        bmp += struct.pack('<i', 2835)
        bmp += struct.pack('<I', 0)
        bmp += struct.pack('<I', 0)
        
        # Generate gradient rows (bottom to top in BMP)
        for y in range(height):
            # Interpolate colors
            t = y / max(height - 1, 1)
            r = int(color1[0] * (1 - t) + color2[0] * t)
            g = int(color1[1] * (1 - t) + color2[1] * t)
            b = int(color1[2] * (1 - t) + color2[2] * t)
            
            row = bytes([b, g, r]) * width
            row += b'\x00' * (row_size - width * 3)
            bmp += row
        
        log.info(f"Generated {width}x{height} gradient BMP")
        return bytes(bmp)


# Preset colors
COLORS = {
    'black': (0, 0, 0),
    'stealth': (10, 10, 10),
    'blue': (0, 60, 120),
    'red': (180, 20, 20),
    'green': (20, 140, 20),
    'white': (240, 240, 240),
}

# Preset gradients
GRADIENTS = {
    'cyber': ((0, 255, 255), (255, 0, 255)),  # Cyan to Magenta
    'fire': ((255, 0, 0), (255, 165, 0)),     # Red to Orange
    'ocean': ((0, 50, 100), (0, 150, 200)),   # Deep blue to cyan
    'matrix': ((0, 20, 0), (0, 255, 0)),      # Dark to bright green
}
