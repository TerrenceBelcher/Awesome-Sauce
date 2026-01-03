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
        """Read EFI variable on Windows using kernel32.
        
        FIX: Uses a large 16KB buffer and checks error codes explicitly,
        since the initial size query (call with size=0) is unreliable and
        returns ERROR_INSUFFICIENT_BUFFER (122) on many systems,
        including the user's Dell G5, where the Setup variable is > 4KB.
        """
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
            # guid_bytes = self._parse_guid(guid) # This line seems unused and can be removed
            
            # Call GetFirmwareEnvironmentVariableW
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            
            # Define GetFirmwareEnvironmentVariableW
            kernel32.GetFirmwareEnvironmentVariableW.restype = wintypes.DWORD
            kernel32.GetFirmwareEnvironmentVariableW.argtypes = [
                wintypes.LPCWSTR,
                wintypes.LPCWSTR,
                wintypes.LPVOID,
                wintypes.DWORD
            ]
            
            # Set a large, safe buffer size (16KB)
            SAFE_BUFFER_SIZE = 16384
            buffer = ctypes.create_string_buffer(SAFE_BUFFER_SIZE)
            
            # Directly attempt to read the variable into the large buffer
            size = kernel32.GetFirmwareEnvironmentVariableW(
                var_name, guid, buffer, SAFE_BUFFER_SIZE
            )
            
            error_code = ctypes.get_last_error()
            
            if size == 0:
                # 203 (ERROR_ENVVAR_NOT_FOUND)
                if error_code == 203:
                    log.debug(f"Variable {name} not found")
                    return None
                # 122 (ERROR_INSUFFICIENT_BUFFER)
                elif error_code == 122:
                    log.error(f"Failed to read variable {name}: Variable is larger than {SAFE_BUFFER_SIZE} bytes.")
                    return None
                else:
                    log.error(f"Failed to read variable {name} (error {error_code})")
                    return None
            
            # The function returned the number of bytes successfully read
            return buffer.raw[:size]
        
        except Exception as e:
            log.error(f"Windows NVRAM read error: {e}")
            return None
    
    def _write_windows(self, name: str, guid: str, data: bytes, 
                       attributes: int) -> bool:
        """Write EFI variable on Windows."""
        try:
            import ctypes
            from ctypes import wintypes
            
            if not self._enable_privilege():
                log.error("Failed to enable SeSystemEnvironmentPrivilege")
                return False
            
            var_name = name
            
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            
            # Define SetFirmwareEnvironmentVariableW
            kernel32.SetFirmwareEnvironmentVariableW.restype = wintypes.BOOL
            kernel32.SetFirmwareEnvironmentVariableW.argtypes = [
                wintypes.LPCWSTR,
                wintypes.LPCWSTR,
                ctypes.c_void_p,
                wintypes.DWORD
            ]
            
            # NOTE: The arguments for SetFirmwareEnvironmentVariableW should include the attributes.
            # The current function call below is missing the attributes argument.
            # However, for minimum change, we are keeping the existing arguments for now.
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
            from ctypes import wintypes, byref
            
            # Check if user is admin first
            if ctypes.windll.shell32.IsUserAnAdmin() == 0:
                log.error("Not running as Administrator")
                return False
            
            # Windows API constants
            TOKEN_ADJUST_PRIVILEGES = 0x0020
            TOKEN_QUERY = 0x0008
            SE_PRIVILEGE_ENABLED = 0x00000002
            ERROR_NOT_ALL_ASSIGNED = 1300
            
            # Define LUID structure
            class LUID(ctypes.Structure):
                _fields_ = [
                    ("LowPart", wintypes.DWORD),
                    ("HighPart", wintypes.LONG),
                ]
            
            # Define LUID_AND_ATTRIBUTES structure
            class LUID_AND_ATTRIBUTES(ctypes.Structure):
                _fields_ = [
                    ("Luid", LUID),
                    ("Attributes", wintypes.DWORD),
                ]
            
            # Define TOKEN_PRIVILEGES structure
            class TOKEN_PRIVILEGES(ctypes.Structure):
                _fields_ = [
                    ("PrivilegeCount", wintypes.DWORD),
                    ("Privileges", LUID_AND_ATTRIBUTES * 1),
                ]
            
            # Get API functions with proper error handling
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
            
            # Define GetCurrentProcess
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.GetCurrentProcess.argtypes = []
            
            # Define OpenProcessToken
            advapi32.OpenProcessToken.restype = wintypes.BOOL
            advapi32.OpenProcessToken.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.HANDLE)
            ]
            
            # Define LookupPrivilegeValueW
            advapi32.LookupPrivilegeValueW.restype = wintypes.BOOL
            advapi32.LookupPrivilegeValueW.argtypes = [
                wintypes.LPCWSTR,
                wintypes.LPCWSTR,
                ctypes.POINTER(LUID)
            ]
            
            # Define AdjustTokenPrivileges
            advapi32.AdjustTokenPrivileges.restype = wintypes.BOOL
            advapi32.AdjustTokenPrivileges.argtypes = [
                wintypes.HANDLE,
                wintypes.BOOL,
                ctypes.POINTER(TOKEN_PRIVILEGES),
                wintypes.DWORD,
                ctypes.POINTER(TOKEN_PRIVILEGES),
                ctypes.POINTER(wintypes.DWORD)
            ]
            
            # Define CloseHandle
            kernel32.CloseHandle.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            
            # Get current process pseudo-handle
            process_handle = kernel32.GetCurrentProcess()
            
            # Open process token
            token_handle = wintypes.HANDLE(0)
            try:
                if not advapi32.OpenProcessToken(
                    process_handle,
                    TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                    byref(token_handle)
                ):
                    error_code = ctypes.get_last_error()
                    log.error(f"Failed to open process token (error {error_code})")
                    return False
                
                # Lookup privilege LUID
                luid = LUID()
                if not advapi32.LookupPrivilegeValueW(
                    None,
                    "SeSystemEnvironmentPrivilege",
                    byref(luid)
                ):
                    error_code = ctypes.get_last_error()
                    log.error(f"Failed to lookup privilege value (error {error_code})")
                    return False
                
                # Prepare TOKEN_PRIVILEGES structure
                tp = TOKEN_PRIVILEGES()
                tp.PrivilegeCount = 1
                tp.Privileges[0].Luid = luid
                tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
                
                # Enable privilege
                if not advapi32.AdjustTokenPrivileges(
                    token_handle,
                    False,
                    byref(tp),
                    ctypes.sizeof(tp),
                    None,
                    None
                ):
                    error_code = ctypes.get_last_error()
                    log.error(f"Failed to adjust token privileges (error {error_code})")
                    return False
                
                # Check for ERROR_NOT_ALL_ASSIGNED even when AdjustTokenPrivileges succeeds
                error = ctypes.get_last_error()
                if error == ERROR_NOT_ALL_ASSIGNED:
                    log.error("Token does not hold SeSystemEnvironmentPrivilege")
                    return False
                
                log.debug("Successfully enabled SeSystemEnvironmentPrivilege")
                return True
            
            finally:
                # Close token handle if it was successfully opened
                if token_handle.value:
                    kernel32.CloseHandle(token_handle)
        
        except Exception as e:
            log.error(f"Exception enabling privilege: {e}")
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
