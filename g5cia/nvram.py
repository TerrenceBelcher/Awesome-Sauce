"""Cross-platform NVRAM/EFI variable access."""

import sys
import os
import struct
import logging
from typing import Optional, Dict
from pathlib import Path

log = logging.getLogger(__name__)


class NVRAMAccess:
    """Cross-platform EFI variable access."""
    
    def __init__(self):
        self.platform = sys.platform
        self.can_access = False
        self._check_access()
    
    def _check_access(self) -> None:
        """Check if we have access to EFI variables."""
        if self.platform == 'win32':
            # On Windows, need admin and SeSystemEnvironmentPrivilege
            try:
                import ctypes
                self.can_access = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                self.can_access = False
        
        elif self.platform.startswith('linux'):
            # On Linux, check for efivarfs mount
            if Path('/sys/firmware/efi/efivars').exists():
                self.can_access = os.access('/sys/firmware/efi/efivars', os.W_OK)
            else:
                self.can_access = False
        
        else:
            log.warning(f"Unsupported platform for NVRAM access: {self.platform}")
    
    def read_variable(self, name: str, guid: str) -> Optional[bytes]:
        """Read EFI variable.
        
        Args:
            name: Variable name (e.g., "Setup")
            guid: Variable GUID
        
        Returns:
            Variable data or None if not found
        """
        if not self.can_access:
            log.error("No NVRAM access - need admin/root privileges")
            return None
        
        if self.platform == 'win32':
            return self._read_windows(name, guid)
        elif self.platform.startswith('linux'):
            return self._read_linux(name, guid)
        
        return None
    
    def write_variable(self, name: str, guid: str, data: bytes, 
                      attributes: int = 0x07) -> bool:
        """Write EFI variable.
        
        Args:
            name: Variable name
            guid: Variable GUID
            data: Variable data
            attributes: EFI variable attributes (default: BS|RT|NV)
        
        Returns:
            True if successful
        """
        if not self.can_access:
            log.error("No NVRAM access - need admin/root privileges")
            return False
        
        if self.platform == 'win32':
            return self._write_windows(name, guid, data, attributes)
        elif self.platform.startswith('linux'):
            return self._write_linux(name, guid, data, attributes)
        
        return False
    
    def _read_windows(self, name: str, guid: str) -> Optional[bytes]:
        """Read EFI variable on Windows using kernel32."""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Enable SeSystemEnvironmentPrivilege
            if not self._enable_privilege():
                log.error("Failed to enable SeSystemEnvironmentPrivilege")
                return None
            
            # Convert name to wide string
            var_name = name
            
            # Parse GUID
            guid_bytes = self._parse_guid(guid)
            
            # Call GetFirmwareEnvironmentVariableW
            kernel32 = ctypes.windll.kernel32
            
            # First call to get size
            size = kernel32.GetFirmwareEnvironmentVariableW(
                var_name, guid, None, 0
            )
            
            if size == 0:
                log.debug(f"Variable {name} not found")
                return None
            
            # Allocate buffer and read
            buffer = ctypes.create_string_buffer(size)
            result = kernel32.GetFirmwareEnvironmentVariableW(
                var_name, guid, buffer, size
            )
            
            if result == 0:
                log.error(f"Failed to read variable {name}")
                return None
            
            return buffer.raw[:result]
        
        except Exception as e:
            log.error(f"Windows NVRAM read error: {e}")
            return None
    
    def _write_windows(self, name: str, guid: str, data: bytes, 
                      attributes: int) -> bool:
        """Write EFI variable on Windows."""
        try:
            import ctypes
            
            if not self._enable_privilege():
                log.error("Failed to enable SeSystemEnvironmentPrivilege")
                return False
            
            var_name = name
            
            kernel32 = ctypes.windll.kernel32
            result = kernel32.SetFirmwareEnvironmentVariableW(
                var_name, guid, data, len(data)
            )
            
            return result != 0
        
        except Exception as e:
            log.error(f"Windows NVRAM write error: {e}")
            return False
    
    def _enable_privilege(self) -> bool:
        """Enable SeSystemEnvironmentPrivilege on Windows."""
        try:
            import ctypes
            from ctypes import wintypes
            
            # This is a simplified version - full implementation would use
            # OpenProcessToken, LookupPrivilegeValue, AdjustTokenPrivileges
            # For now, just return True if admin
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def _read_linux(self, name: str, guid: str) -> Optional[bytes]:
        """Read EFI variable on Linux using efivarfs."""
        try:
            # efivarfs naming: VariableName-guid
            var_path = Path(f'/sys/firmware/efi/efivars/{name}-{guid}')
            
            if not var_path.exists():
                log.debug(f"Variable {name} not found")
                return None
            
            # Read file (first 4 bytes are attributes)
            data = var_path.read_bytes()
            
            # Skip attributes
            return data[4:]
        
        except Exception as e:
            log.error(f"Linux NVRAM read error: {e}")
            return None
    
    def _write_linux(self, name: str, guid: str, data: bytes, 
                     attributes: int) -> bool:
        """Write EFI variable on Linux using efivarfs."""
        try:
            var_path = Path(f'/sys/firmware/efi/efivars/{name}-{guid}')
            
            # If exists, make writable
            if var_path.exists():
                os.system(f'chattr -i {var_path}')
            
            # Prepend attributes
            full_data = struct.pack('<I', attributes) + data
            
            # Write
            var_path.write_bytes(full_data)
            
            # Make immutable again
            os.system(f'chattr +i {var_path}')
            
            return True
        
        except Exception as e:
            log.error(f"Linux NVRAM write error: {e}")
            return False
    
    def _parse_guid(self, guid: str) -> str:
        """Parse GUID string for Windows API."""
        # Windows expects GUID in registry format
        return '{' + guid + '}'
    
    def backup_setup(self, backup_path: str) -> bool:
        """Backup Setup variable to file."""
        # Setup GUID (common)
        setup_guid = "EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9"
        
        data = self.read_variable("Setup", setup_guid)
        if not data:
            log.error("Failed to read Setup variable")
            return False
        
        Path(backup_path).write_bytes(data)
        log.info(f"Setup backed up to {backup_path} ({len(data)} bytes)")
        return True
    
    def restore_setup(self, backup_path: str) -> bool:
        """Restore Setup variable from file."""
        setup_guid = "EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9"
        
        data = Path(backup_path).read_bytes()
        
        if self.write_variable("Setup", setup_guid, data):
            log.info(f"Setup restored from {backup_path}")
            return True
        else:
            log.error("Failed to restore Setup variable")
            return False


def print_nvram_report() -> None:
    """Print NVRAM access report."""
    nvram = NVRAMAccess()
    
    print("\n" + "="*70)
    print("NVRAM ACCESS REPORT")
    print("="*70)
    print(f"Platform: {nvram.platform}")
    print(f"NVRAM Access: {'[OK] Available' if nvram.can_access else '[FAIL] Not available'}")
    
    if not nvram.can_access:
        if nvram.platform == 'win32':
            print("\nTo enable NVRAM access on Windows:")
            print("  1. Run as Administrator")
            print("  2. Ensure SeSystemEnvironmentPrivilege is enabled")
        elif nvram.platform.startswith('linux'):
            print("\nTo enable NVRAM access on Linux:")
            print("  1. Run as root (sudo)")
            print("  2. Ensure efivarfs is mounted: mount -t efivarfs none /sys/firmware/efi/efivars")
    
    print("="*70 + "\n")
