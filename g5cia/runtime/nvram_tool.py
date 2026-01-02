"""NVRAM unlock tool for instant unlock without BIOS reflash."""

import logging
from typing import List, Tuple, Optional
from pathlib import Path

from ..nvram import NVRAMAccess
from ..offsets import get_offset
from ..firmware.ifr import IFRParser

log = logging.getLogger(__name__)


class NVRAMUnlocker:
    """Unlock BIOS settings via NVRAM without reflashing."""
    
    # Setup GUID for Dell G5 5090 (common Setup GUID)
    SETUP_GUID = "EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9"
    
    # Lock settings to unlock
    LOCK_SETTINGS = [
        ('CfgLk', 'CFG Lock (MSR 0xE2)'),
        ('OcLk', 'Overclocking Lock'),
        ('PlLk', 'Power Limit Lock'),
        ('BiosLk', 'BIOS Interface Lock'),
    ]
    
    def __init__(self, use_ifr_parser: bool = True):
        """Initialize NVRAM unlocker.
        
        Args:
            use_ifr_parser: Try to use IFR parser for dynamic offset discovery
        """
        self.nvram = NVRAMAccess()
        self.use_ifr_parser = use_ifr_parser
        self.ifr_parser: Optional[IFRParser] = None
        self.setup_data: Optional[bytes] = None
        
    def _load_setup(self) -> bool:
        """Load current Setup variable from NVRAM."""
        if not self.nvram.can_access:
            log.error("No NVRAM access - need admin/root privileges")
            return False
        
        self.setup_data = self.nvram.read_variable("Setup", self.SETUP_GUID)
        
        if not self.setup_data:
            log.error("Failed to read Setup variable from NVRAM")
            return False
        
        log.info(f"Loaded Setup variable ({len(self.setup_data)} bytes)")
        return True
    
    def _discover_offsets(self) -> bool:
        """Discover offsets using IFR parser."""
        if not self.use_ifr_parser:
            log.info("IFR parser disabled, using static offsets")
            return True
        
        if not self.setup_data:
            log.error("Setup data not loaded")
            return False
        
        try:
            self.ifr_parser = IFRParser()
            offsets = self.ifr_parser.parse(self.setup_data)
            
            if offsets:
                log.info(f"IFR parser discovered {len(offsets)} settings")
                return True
            else:
                log.warning("IFR parser found no settings, falling back to static offsets")
                return True
        
        except Exception as e:
            log.warning(f"IFR parser failed: {e}, falling back to static offsets")
            return True
    
    def _get_offset(self, setting_name: str) -> Optional[Tuple[int, int]]:
        """Get offset for a setting.
        
        Tries IFR parser first, then falls back to static offsets.
        
        Args:
            setting_name: Setting name (e.g., 'CfgLk')
            
        Returns:
            Tuple of (offset, size) or None if not found
        """
        # Try IFR parser first
        if self.ifr_parser:
            offset_info = self.ifr_parser.get_offset_info(setting_name)
            if offset_info:
                log.debug(f"Found {setting_name} via IFR parser: 0x{offset_info.offset:x}")
                return (offset_info.offset, offset_info.size)
        
        # Fall back to static offsets
        try:
            offset, size = get_offset(setting_name)
            log.debug(f"Found {setting_name} via static offsets: 0x{offset:x}")
            return (offset, size)
        except KeyError:
            log.warning(f"Setting {setting_name} not found in static offsets")
            return None
    
    def nv_unlock(self, dry: bool = False) -> List[Tuple[str, bool, str]]:
        """Unlock CFG/OC/PL locks via NVRAM without reflashing.
        
        Args:
            dry: If True, only simulate (don't actually modify NVRAM)
            
        Returns:
            List of tuples: (setting_name, success, message)
        """
        results = []
        
        # Load current Setup
        if not self._load_setup():
            return [('NVRAM Access', False, 'Failed to load Setup variable')]
        
        # Discover offsets
        if not self._discover_offsets():
            return [('Offset Discovery', False, 'Failed to discover offsets')]
        
        # Create backup
        if not dry:
            backup_path = Path.home() / '.g5cia_setup_backup.bin'
            try:
                backup_path.write_bytes(self.setup_data)
                log.info(f"Created backup at {backup_path}")
            except Exception as e:
                log.warning(f"Failed to create backup: {e}")
        
        # Unlock each setting
        setup_modified = False
        modified_data = bytearray(self.setup_data)
        
        for setting_name, description in self.LOCK_SETTINGS:
            try:
                offset_info = self._get_offset(setting_name)
                
                if not offset_info:
                    results.append((description, False, f'Offset not found'))
                    continue
                
                offset, size = offset_info
                
                if offset >= len(modified_data):
                    results.append((description, False, f'Offset 0x{offset:x} beyond Setup size'))
                    continue
                
                # Read current value
                if size == 1:
                    current_val = modified_data[offset]
                elif size == 2:
                    current_val = int.from_bytes(modified_data[offset:offset+2], 'little')
                else:
                    current_val = int.from_bytes(modified_data[offset:offset+size], 'little')
                
                # Check if already unlocked
                if current_val == 0:
                    results.append((description, True, f'Already unlocked'))
                    continue
                
                if dry:
                    results.append((description, True, f'[DRY] Would unlock @0x{offset:X} (current={current_val})'))
                else:
                    # Set to 0 (unlocked)
                    if size == 1:
                        modified_data[offset] = 0
                    elif size == 2:
                        modified_data[offset:offset+2] = (0).to_bytes(2, 'little')
                    else:
                        modified_data[offset:offset+size] = (0).to_bytes(size, 'little')
                    
                    setup_modified = True
                    results.append((description, True, f'Unlocked @0x{offset:X} (was {current_val})'))
                    log.info(f"Unlocked {description} @ 0x{offset:x}")
            
            except Exception as e:
                results.append((description, False, f'Error: {e}'))
                log.error(f"Error unlocking {setting_name}: {e}")
        
        # Write modified Setup back to NVRAM
        if setup_modified and not dry:
            log.info("Writing modified Setup to NVRAM...")
            
            if self.nvram.write_variable("Setup", self.SETUP_GUID, bytes(modified_data)):
                # Verify by reading back
                verify_data = self.nvram.read_variable("Setup", self.SETUP_GUID)
                
                if verify_data and verify_data == bytes(modified_data):
                    log.info("[OK] NVRAM unlock successful and verified")
                    results.append(('Verification', True, 'Write verified successfully'))
                else:
                    log.warning("[WARN] NVRAM write may have failed - verification mismatch")
                    results.append(('Verification', False, 'Write verification failed'))
            else:
                log.error("[FAIL] Failed to write Setup to NVRAM")
                results.append(('NVRAM Write', False, 'Write operation failed'))
        
        return results
    
    def lock(self, settings: Optional[List[str]] = None, dry: bool = False) -> List[Tuple[str, bool, str]]:
        """Re-lock settings (reverse of unlock).
        
        Args:
            settings: List of setting names to lock, or None for all
            dry: If True, only simulate
            
        Returns:
            List of tuples: (setting_name, success, message)
        """
        results = []
        
        if not self._load_setup():
            return [('NVRAM Access', False, 'Failed to load Setup variable')]
        
        if not self._discover_offsets():
            return [('Offset Discovery', False, 'Failed to discover offsets')]
        
        # Determine which settings to lock
        if settings is None:
            lock_list = self.LOCK_SETTINGS
        else:
            lock_list = [(s, s) for s in settings]
        
        setup_modified = False
        modified_data = bytearray(self.setup_data)
        
        for setting_name, description in lock_list:
            try:
                offset_info = self._get_offset(setting_name)
                
                if not offset_info:
                    results.append((description, False, 'Offset not found'))
                    continue
                
                offset, size = offset_info
                
                if offset >= len(modified_data):
                    results.append((description, False, f'Offset 0x{offset:x} beyond Setup size'))
                    continue
                
                # Read current value
                if size == 1:
                    current_val = modified_data[offset]
                else:
                    current_val = int.from_bytes(modified_data[offset:offset+size], 'little')
                
                # Check if already locked
                if current_val == 1:
                    results.append((description, True, 'Already locked'))
                    continue
                
                if dry:
                    results.append((description, True, f'[DRY] Would lock @0x{offset:X}'))
                else:
                    # Set to 1 (locked)
                    if size == 1:
                        modified_data[offset] = 1
                    else:
                        modified_data[offset:offset+size] = (1).to_bytes(size, 'little')
                    
                    setup_modified = True
                    results.append((description, True, f'Locked @0x{offset:X}'))
            
            except Exception as e:
                results.append((description, False, f'Error: {e}'))
        
        # Write back if modified
        if setup_modified and not dry:
            if self.nvram.write_variable("Setup", self.SETUP_GUID, bytes(modified_data)):
                results.append(('NVRAM Write', True, 'Successfully written'))
            else:
                results.append(('NVRAM Write', False, 'Write failed'))
        
        return results
    
    def restore_backup(self, backup_path: Optional[Path] = None) -> bool:
        """Restore Setup from backup.
        
        Args:
            backup_path: Path to backup file, or None for default location
            
        Returns:
            True if successful
        """
        if backup_path is None:
            backup_path = Path.home() / '.g5cia_setup_backup.bin'
        
        if not backup_path.exists():
            log.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            backup_data = backup_path.read_bytes()
            
            if self.nvram.write_variable("Setup", self.SETUP_GUID, backup_data):
                log.info(f"[OK] Restored Setup from {backup_path}")
                return True
            else:
                log.error("Failed to restore Setup")
                return False
        
        except Exception as e:
            log.error(f"Error restoring backup: {e}")
            return False
