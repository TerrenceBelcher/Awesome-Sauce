"""Advanced patching modules."""

from .optionrom import OptionROMManager, OptionROM, ROMInfo
from .acpi import ACPIPatcher, ACPITable, ACPIPatch

__all__ = [
    'OptionROMManager',
    'OptionROM',
    'ROMInfo',
    'ACPIPatcher',
    'ACPITable',
    'ACPIPatch',
]
