"""IFR (Internal Forms Representation) parser for dynamic offset discovery.

This module parses UEFI IFR opcodes to dynamically discover Setup variable 
offsets at runtime, eliminating dependency on static offset maps that break 
across BIOS versions.

Reference: UEFI Specification 2.9 - Chapter 33 (Human Interface Infrastructure)
"""

import struct
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import IntEnum

log = logging.getLogger(__name__)


class IFROpcode(IntEnum):
    """IFR operation codes."""
    FORM_SET = 0x0E
    END = 0x29
    FORM = 0x01
    SUBTITLE = 0x02
    TEXT = 0x03
    GRAPHIC = 0x04
    ONE_OF = 0x05
    CHECKBOX = 0x06
    NUMERIC = 0x07
    PASSWORD = 0x08
    ONE_OF_OPTION = 0x09
    SUPPRESS_IF = 0x0A
    LOCKED = 0x0B
    ACTION = 0x0C
    RESET_BUTTON = 0x0D
    VARSTORE = 0x24
    VARSTORE_EFI = 0x26
    VARSTORE_NAME_VALUE = 0x25
    GUID = 0x0F
    REF = 0x0C
    NO_SUBMIT_IF = 0x10
    INCONSISTENT_IF = 0x11
    EQ_ID_VAL = 0x12
    EQ_ID_ID = 0x13
    EQ_ID_LIST = 0x14
    AND = 0x15
    OR = 0x16
    NOT = 0x17
    RULE = 0x18
    GRAYOUT_IF = 0x19
    DATE = 0x1A
    TIME = 0x1B
    STRING = 0x1C
    REFRESH = 0x1D
    DISABLE_IF = 0x1E
    TO_LOWER = 0x20
    TO_UPPER = 0x21
    MAP = 0x22
    ORDERED_LIST = 0x23
    DEFAULT = 0x5B
    GET = 0x2B
    SET = 0x2C
    READ = 0x2D
    WRITE = 0x2E


@dataclass
class OffsetInfo:
    """Information about a discovered offset."""
    name: str
    offset: int
    size: int
    varstore_id: int
    opcode: int
    prompt_id: Optional[int] = None
    help_id: Optional[int] = None
    default_value: Optional[int] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    options: Optional[Dict[str, int]] = None


@dataclass
class Setting:
    """A complete BIOS setting with all metadata."""
    name: str
    offset: int
    size: int
    description: str
    setting_type: str  # 'checkbox', 'numeric', 'oneof'
    current_value: Optional[int] = None
    default_value: Optional[int] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    options: Optional[Dict[str, int]] = None


@dataclass
class VarStore:
    """Variable storage definition."""
    varstore_id: int
    guid: bytes
    name: str
    size: int


class IFRParser:
    """Parse IFR opcodes to discover BIOS setting offsets dynamically."""
    
    def __init__(self):
        self.offsets: Dict[str, OffsetInfo] = {}
        self.varstores: Dict[int, VarStore] = {}
        self.strings: Dict[int, str] = {}
        self.current_varstore: Optional[int] = None
        self.cache_valid = False
        
    def parse(self, setup_data: bytes) -> Dict[str, OffsetInfo]:
        """Parse IFR data and return offset map.
        
        Args:
            setup_data: Raw IFR/HII data from Setup driver
            
        Returns:
            Dictionary mapping setting names to OffsetInfo
        """
        if not setup_data or len(setup_data) < 4:
            log.warning("Invalid or empty setup data")
            return {}
        
        log.info(f"Parsing IFR data ({len(setup_data)} bytes)")
        
        # Reset state
        self.offsets = {}
        self.varstores = {}
        self.strings = {}
        self.current_varstore = None
        
        # First pass: extract string packages
        self._extract_strings(setup_data)
        
        # Second pass: parse IFR opcodes
        self._parse_opcodes(setup_data)
        
        self.cache_valid = True
        log.info(f"Discovered {len(self.offsets)} settings from IFR data")
        
        return self.offsets
    
    def _extract_strings(self, data: bytes) -> None:
        """Extract HII string packages.
        
        String packages contain human-readable names referenced by IFR opcodes.
        Format: String ID -> UTF-16 string
        """
        # Look for HII Package List Header
        # Signature: EFI_HII_PACKAGE_LIST_GUID
        pos = 0
        while pos < len(data) - 16:
            # Simple heuristic: look for string markers
            # Real implementation would parse full package structure
            if data[pos:pos+2] == b'\x02\x00':  # String package type
                try:
                    # Skip to string data
                    str_pos = pos + 4
                    string_id = 1
                    
                    while str_pos < len(data) - 2:
                        # Read length byte
                        if data[str_pos] == 0:
                            break
                        
                        # Try to read UTF-16 string
                        end_pos = str_pos
                        while end_pos < len(data) - 1:
                            if data[end_pos] == 0 and data[end_pos + 1] == 0:
                                break
                            end_pos += 2
                        
                        if end_pos > str_pos and end_pos < len(data):
                            try:
                                string_bytes = data[str_pos:end_pos]
                                string_val = string_bytes.decode('utf-16-le', errors='ignore').strip()
                                
                                if string_val and len(string_val) < 100:
                                    self.strings[string_id] = string_val
                                    string_id += 1
                            except:
                                pass
                        
                        str_pos = end_pos + 2
                        
                        if str_pos >= pos + 512:  # Limit string scan
                            break
                except:
                    pass
            
            pos += 1
        
        log.debug(f"Extracted {len(self.strings)} strings from HII data")
    
    def _parse_opcodes(self, data: bytes) -> None:
        """Parse IFR opcodes to discover settings."""
        pos = 0
        
        while pos < len(data) - 2:
            # IFR opcode format: [opcode:1][length:1][data...]
            try:
                opcode = data[pos]
                
                # Check for extended opcode
                if opcode == 0x5C:  # Extended opcode prefix
                    if pos + 2 < len(data):
                        opcode = data[pos + 1]
                        length = data[pos + 2] if pos + 2 < len(data) else 0
                        pos += 1
                    else:
                        pos += 1
                        continue
                else:
                    length = data[pos + 1] if pos + 1 < len(data) else 0
                
                if length < 2 or length > 255:
                    pos += 1
                    continue
                
                if pos + length > len(data):
                    break
                
                opcode_data = data[pos + 2:pos + length]
                
                # Parse specific opcodes
                if opcode == IFROpcode.VARSTORE and len(opcode_data) >= 4:
                    self._parse_varstore(opcode_data)
                
                elif opcode == IFROpcode.VARSTORE_EFI and len(opcode_data) >= 4:
                    self._parse_varstore_efi(opcode_data)
                
                elif opcode == IFROpcode.ONE_OF and len(opcode_data) >= 6:
                    self._parse_one_of(opcode_data)
                
                elif opcode == IFROpcode.CHECKBOX and len(opcode_data) >= 6:
                    self._parse_checkbox(opcode_data)
                
                elif opcode == IFROpcode.NUMERIC and len(opcode_data) >= 8:
                    self._parse_numeric(opcode_data)
                
                elif opcode == IFROpcode.ONE_OF_OPTION and len(opcode_data) >= 4:
                    self._parse_one_of_option(opcode_data)
                
                pos += length
                
            except Exception as e:
                log.debug(f"Error parsing opcode at 0x{pos:x}: {e}")
                pos += 1
    
    def _parse_varstore(self, data: bytes) -> None:
        """Parse IFR_VARSTORE opcode."""
        try:
            # Format: GUID(16) + VarStoreId(2) + Size(2) + Name(variable)
            if len(data) < 20:
                return
            
            guid = data[0:16]
            varstore_id = struct.unpack('<H', data[16:18])[0]
            size = struct.unpack('<H', data[18:20])[0]
            
            # Name is null-terminated string after fixed fields
            name_data = data[20:]
            name = ""
            for i in range(0, len(name_data) - 1, 2):
                if name_data[i] == 0 and name_data[i + 1] == 0:
                    break
                try:
                    name += chr(name_data[i])
                except:
                    pass
            
            self.varstores[varstore_id] = VarStore(
                varstore_id=varstore_id,
                guid=guid,
                name=name or f"VarStore_{varstore_id}",
                size=size
            )
            
            # Set as current varstore for subsequent settings
            self.current_varstore = varstore_id
            
            log.debug(f"VarStore: ID={varstore_id}, Size={size}, Name={name}")
            
        except Exception as e:
            log.debug(f"Error parsing VARSTORE: {e}")
    
    def _parse_varstore_efi(self, data: bytes) -> None:
        """Parse IFR_VARSTORE_EFI opcode."""
        try:
            # Format: VarStoreId(2) + GUID(16) + Attributes(4) + Size(2) + Name(variable)
            if len(data) < 24:
                return
            
            varstore_id = struct.unpack('<H', data[0:2])[0]
            guid = data[2:18]
            attributes = struct.unpack('<I', data[18:22])[0]
            size = struct.unpack('<H', data[22:24])[0] if len(data) >= 24 else 0
            
            # Name
            name_data = data[24:] if len(data) > 24 else b''
            name = ""
            for i in range(0, len(name_data) - 1, 2):
                if name_data[i] == 0 and name_data[i + 1] == 0:
                    break
                try:
                    name += chr(name_data[i])
                except:
                    pass
            
            self.varstores[varstore_id] = VarStore(
                varstore_id=varstore_id,
                guid=guid,
                name=name or f"VarStore_{varstore_id}",
                size=size
            )
            
            self.current_varstore = varstore_id
            
            log.debug(f"VarStore EFI: ID={varstore_id}, Size={size}, Name={name}")
            
        except Exception as e:
            log.debug(f"Error parsing VARSTORE_EFI: {e}")
    
    def _parse_one_of(self, data: bytes) -> None:
        """Parse IFR_ONE_OF opcode (dropdown selection)."""
        try:
            # Format: Prompt(2) + Help(2) + QuestionFlags(1) + QuestionId(2) + 
            #         VarStoreId(2) + VarOffset(2) + Flags(1) + Size(1) + ...
            
            if len(data) < 12:
                return
            
            prompt_id = struct.unpack('<H', data[0:2])[0]
            help_id = struct.unpack('<H', data[2:4])[0]
            question_id = struct.unpack('<H', data[5:7])[0]
            varstore_id = struct.unpack('<H', data[7:9])[0]
            var_offset = struct.unpack('<H', data[9:11])[0]
            
            # Size is at different positions depending on format
            size = data[12] if len(data) > 12 else 1
            
            # Get human-readable name from strings
            name = self.strings.get(prompt_id, f"Setting_{var_offset:04X}")
            
            # Clean up name for use as identifier
            name = self._clean_name(name)
            
            offset_info = OffsetInfo(
                name=name,
                offset=var_offset,
                size=size,
                varstore_id=varstore_id,
                opcode=IFROpcode.ONE_OF,
                prompt_id=prompt_id,
                help_id=help_id,
                options={}
            )
            
            self.offsets[name] = offset_info
            
            log.debug(f"OneOf: {name} @ offset 0x{var_offset:x} (size={size})")
            
        except Exception as e:
            log.debug(f"Error parsing ONE_OF: {e}")
    
    def _parse_checkbox(self, data: bytes) -> None:
        """Parse IFR_CHECKBOX opcode (boolean setting)."""
        try:
            if len(data) < 12:
                return
            
            prompt_id = struct.unpack('<H', data[0:2])[0]
            help_id = struct.unpack('<H', data[2:4])[0]
            question_id = struct.unpack('<H', data[5:7])[0]
            varstore_id = struct.unpack('<H', data[7:9])[0]
            var_offset = struct.unpack('<H', data[9:11])[0]
            
            flags = data[11] if len(data) > 11 else 0
            size = 1  # Checkboxes are always 1 byte
            
            name = self.strings.get(prompt_id, f"Setting_{var_offset:04X}")
            name = self._clean_name(name)
            
            offset_info = OffsetInfo(
                name=name,
                offset=var_offset,
                size=size,
                varstore_id=varstore_id,
                opcode=IFROpcode.CHECKBOX,
                prompt_id=prompt_id,
                help_id=help_id,
                options={'Disabled': 0, 'Enabled': 1}
            )
            
            self.offsets[name] = offset_info
            
            log.debug(f"Checkbox: {name} @ offset 0x{var_offset:x}")
            
        except Exception as e:
            log.debug(f"Error parsing CHECKBOX: {e}")
    
    def _parse_numeric(self, data: bytes) -> None:
        """Parse IFR_NUMERIC opcode (numeric input)."""
        try:
            if len(data) < 16:
                return
            
            prompt_id = struct.unpack('<H', data[0:2])[0]
            help_id = struct.unpack('<H', data[2:4])[0]
            question_id = struct.unpack('<H', data[5:7])[0]
            varstore_id = struct.unpack('<H', data[7:9])[0]
            var_offset = struct.unpack('<H', data[9:11])[0]
            
            flags = data[11] if len(data) > 11 else 0
            size = data[12] if len(data) > 12 else 1
            
            # Min/max values depend on size
            min_val = None
            max_val = None
            
            if len(data) >= 16:
                if size == 1:
                    min_val = data[13]
                    max_val = data[14]
                elif size == 2:
                    min_val = struct.unpack('<H', data[13:15])[0] if len(data) >= 15 else 0
                    max_val = struct.unpack('<H', data[15:17])[0] if len(data) >= 17 else 0
            
            name = self.strings.get(prompt_id, f"Setting_{var_offset:04X}")
            name = self._clean_name(name)
            
            offset_info = OffsetInfo(
                name=name,
                offset=var_offset,
                size=size,
                varstore_id=varstore_id,
                opcode=IFROpcode.NUMERIC,
                prompt_id=prompt_id,
                help_id=help_id,
                min_value=min_val,
                max_value=max_val
            )
            
            self.offsets[name] = offset_info
            
            log.debug(f"Numeric: {name} @ offset 0x{var_offset:x} (size={size}, min={min_val}, max={max_val})")
            
        except Exception as e:
            log.debug(f"Error parsing NUMERIC: {e}")
    
    def _parse_one_of_option(self, data: bytes) -> None:
        """Parse IFR_ONE_OF_OPTION opcode (option value)."""
        try:
            # This provides option values for the last ONE_OF parsed
            # Format: Option(2) + Flags(1) + Type(1) + Value(variable)
            
            if len(data) < 4:
                return
            
            option_id = struct.unpack('<H', data[0:2])[0]
            flags = data[2]
            option_type = data[3]
            
            # Value depends on type
            value = 0
            if len(data) >= 5:
                if option_type == 0:  # UINT8
                    value = data[4]
                elif option_type == 1:  # UINT16
                    value = struct.unpack('<H', data[4:6])[0] if len(data) >= 6 else 0
                elif option_type == 2:  # UINT32
                    value = struct.unpack('<I', data[4:8])[0] if len(data) >= 8 else 0
            
            option_name = self.strings.get(option_id, f"Option_{value}")
            
            log.debug(f"Option: {option_name} = {value}")
            
        except Exception as e:
            log.debug(f"Error parsing ONE_OF_OPTION: {e}")
    
    def _clean_name(self, name: str) -> str:
        """Clean up setting name for use as identifier."""
        # Remove special characters, spaces, etc.
        clean = ""
        for char in name:
            if char.isalnum() or char in "_-":
                clean += char
            elif char == " ":
                clean += "_"
        
        # Remove trailing/leading underscores
        clean = clean.strip("_")
        
        # Limit length
        if len(clean) > 50:
            clean = clean[:50]
        
        return clean or "UnknownSetting"
    
    def find_offset(self, name: str) -> Optional[int]:
        """Find offset for a setting by name.
        
        Args:
            name: Setting name (supports fuzzy matching)
            
        Returns:
            Offset or None if not found
        """
        # Exact match
        if name in self.offsets:
            return self.offsets[name].offset
        
        # Case-insensitive match
        name_lower = name.lower()
        for setting_name, info in self.offsets.items():
            if setting_name.lower() == name_lower:
                return info.offset
        
        # Partial match
        for setting_name, info in self.offsets.items():
            if name_lower in setting_name.lower():
                return info.offset
        
        return None
    
    def get_all_settings(self) -> List[Setting]:
        """Get all discovered settings as Setting objects.
        
        Returns:
            List of Setting objects with complete metadata
        """
        settings = []
        
        for name, info in self.offsets.items():
            # Determine setting type
            setting_type = "unknown"
            if info.opcode == IFROpcode.CHECKBOX:
                setting_type = "checkbox"
            elif info.opcode == IFROpcode.NUMERIC:
                setting_type = "numeric"
            elif info.opcode == IFROpcode.ONE_OF:
                setting_type = "oneof"
            
            # Get description from help string
            description = ""
            if info.help_id and info.help_id in self.strings:
                description = self.strings[info.help_id]
            elif info.prompt_id and info.prompt_id in self.strings:
                description = self.strings[info.prompt_id]
            
            setting = Setting(
                name=name,
                offset=info.offset,
                size=info.size,
                description=description or name,
                setting_type=setting_type,
                default_value=info.default_value,
                min_value=info.min_value,
                max_value=info.max_value,
                options=info.options
            )
            
            settings.append(setting)
        
        return settings
    
    def get_offset_info(self, name: str) -> Optional[OffsetInfo]:
        """Get detailed offset information by name.
        
        Args:
            name: Setting name
            
        Returns:
            OffsetInfo or None if not found
        """
        return self.offsets.get(name)
