"""ReBAR (Resizable BAR) driver injection."""

import logging
import struct
from typing import Optional
from pathlib import Path
import urllib.request

from .image import ImageParser, FirmwareVolume
from .utils import checksum8, guid_to_str

log = logging.getLogger(__name__)

# NvStrapsReBar driver URL and info
REBAR_DRIVER_URL = "https://github.com/xCuri0/ReBarUEFI/raw/main/NvStrapsReBar/NvStrapsReBar.ffs"
REBAR_DRIVER_GUID = "9E8EEE1E-BE0D-4AC9-BA7F-2B9C8F856A96"


class ReBarInjector:
    """ReBAR driver injection handler."""
    
    def __init__(self, parser: ImageParser):
        self.parser = parser
        self.driver_data: Optional[bytes] = None
    
    def download_driver(self, local_path: Optional[str] = None) -> bool:
        """Download NvStrapsReBar.ffs driver.
        
        Args:
            local_path: Optional local path to load from instead of downloading
        
        Returns:
            True if successful
        """
        if local_path and Path(local_path).exists():
            log.info(f"Loading ReBAR driver from {local_path}")
            self.driver_data = Path(local_path).read_bytes()
        else:
            log.info(f"Downloading ReBAR driver from {REBAR_DRIVER_URL}")
            try:
                with urllib.request.urlopen(REBAR_DRIVER_URL, timeout=30) as response:
                    self.driver_data = response.read()
            except Exception as e:
                log.error(f"Failed to download ReBAR driver: {e}")
                return False
        
        # Validate FFS structure
        if not self._validate_driver():
            log.error("ReBAR driver validation failed")
            self.driver_data = None
            return False
        
        log.info(f"ReBAR driver loaded ({len(self.driver_data)} bytes)")
        return True
    
    def _validate_driver(self) -> bool:
        """Validate FFS structure of driver."""
        if not self.driver_data or len(self.driver_data) < 0x18:
            return False
        
        # Check GUID
        guid_bytes = self.driver_data[0:16]
        guid = guid_to_str(guid_bytes)
        
        # Verify it looks like a valid FFS file
        # Check file type (should be DRIVER = 0x07)
        file_type = self.driver_data[0x12]
        
        if file_type != 0x07:
            log.warning(f"Unexpected file type: 0x{file_type:02X} (expected 0x07)")
        
        # Check size
        size_bytes = self.driver_data[0x14:0x17] + b'\x00'
        file_size = struct.unpack('<I', size_bytes)[0]
        
        if file_size != len(self.driver_data):
            log.error(f"Size mismatch: header says {file_size}, actual {len(self.driver_data)}")
            return False
        
        log.debug(f"ReBAR driver GUID: {guid}, type: 0x{file_type:02X}, size: {file_size}")
        return True
    
    def inject(self, data: bytearray, force: bool = False) -> bool:
        """Inject ReBAR driver into firmware.
        
        Args:
            data: Firmware data (will be modified in-place)
            force: Force injection even with Boot Guard
        
        Returns:
            True if successful
        """
        if not self.driver_data:
            log.error("ReBAR driver not loaded - call download_driver() first")
            return False
        
        # Check for Boot Guard
        from .security import SecurityAnalyzer
        analyzer = SecurityAnalyzer(bytes(data))
        status = analyzer.analyze()
        
        if status.boot_guard_verified and not force:
            log.error("CRITICAL: Boot Guard Verified Boot detected - injection will BRICK!")
            log.error("Use --force to override (NOT RECOMMENDED)")
            return False
        
        # Find DXE volume
        dxe_vol = self.parser.find_dxe_volume()
        if not dxe_vol:
            log.error("Could not find DXE volume for injection")
            return False
        
        log.info(f"DXE volume found at 0x{dxe_vol.offset:x}")
        
        # Find free space at end of volume
        min_size = len(self.driver_data) + 0x100  # Extra space for alignment
        free_offset = self.parser.find_free_space(dxe_vol, min_size)
        
        if not free_offset:
            log.error(f"No free space in DXE volume for {min_size} bytes")
            return False
        
        log.info(f"Injecting ReBAR driver at 0x{free_offset:x}")
        
        # Inject driver
        data[free_offset:free_offset+len(self.driver_data)] = self.driver_data
        
        # Recalculate volume checksum
        from .patcher import Patcher
        patcher = Patcher(bytes(data))
        patcher.data = data  # Use same bytearray
        patcher.recalc_fv_checksum(dxe_vol.offset)
        
        log.info("✓ ReBAR driver injected successfully")
        return True


def inject_rebar_driver(image_path: str, output_path: str, 
                        driver_path: Optional[str] = None,
                        force: bool = False) -> bool:
    """Standalone ReBAR injection function.
    
    Args:
        image_path: Input BIOS image
        output_path: Output path for modded image
        driver_path: Optional local driver path
        force: Force injection despite Boot Guard
    
    Returns:
        True if successful
    """
    log.info(f"ReBAR injection: {image_path} -> {output_path}")
    
    # Load image
    data = Path(image_path).read_bytes()
    parser = ImageParser(data)
    
    if not parser.parse():
        log.error("Failed to parse firmware image")
        return False
    
    # Create injector
    injector = ReBarInjector(parser)
    
    # Download/load driver
    if not injector.download_driver(driver_path):
        return False
    
    # Inject
    data_array = bytearray(data)
    if not injector.inject(data_array, force):
        return False
    
    # Save
    Path(output_path).write_bytes(data_array)
    log.info(f"Modded image saved to {output_path}")
    
    return True
