"""Platform abstraction for multi-system support."""

from .hal import HAL, PlatformInfo
from .dell_g5_5090 import DELL_G5_5090
from .dell_g5_5000 import DELL_G5_5000
from .dell_xps_8940 import DELL_XPS_8940
from .alienware import ALIENWARE_AURORA_R10

__all__ = [
    'HAL',
    'PlatformInfo',
    'DELL_G5_5090',
    'DELL_G5_5000',
    'DELL_XPS_8940',
    'ALIENWARE_AURORA_R10',
]
