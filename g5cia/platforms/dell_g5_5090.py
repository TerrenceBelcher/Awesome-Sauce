"""Dell G5 5090 platform profile."""

from .hal import HAL, PlatformInfo

# Import existing offset map
from ..offsets import OFFSETS as G5_5090_OFFSETS


# Create platform profile
DELL_G5_5090 = PlatformInfo(
    name="Dell G5 5090",
    codename="Inspiron 5090",
    manufacturer="Dell",
    pch="B365",
    
    # Supported CPUIDs (9th gen Intel Core)
    supported_cpuids=[
        0x906EA,  # i9-9900
        0x906EB,  # i7-9700
        0x906EC,  # i5-9600/9400
        0x906ED,  # i3-9100
    ],
    
    # VRM limits (Dell G5 5090 specific)
    vrm_sustained=95,   # PL1 - sustained load
    vrm_burst=115,      # PL2 - burst load
    vrm_max_safe=120,   # Absolute maximum
    
    # Static offsets from existing offset map
    static_offsets={k: (v[0], v[1]) for k, v in G5_5090_OFFSETS.items()},
    
    # Known BIOS versions
    bios_versions=[
        '1.8.0', '1.9.0', '1.10.0', '1.11.0', 
        '1.12.0', '1.13.0', '1.14.0', '1.15.0', '1.16.0'
    ],
    
    # BIOS signatures for detection
    signatures=[
        b'Dell Inc.\x00',
        b'G5 5090\x00',
        b'Inspiron 5090\x00',
        b'OptiPlex 5090\x00',  # Similar platform
    ],
    
    # Feature support
    supports_rebar=True,
    supports_above_4g=True,
    supports_me_disable=True,
)


# Register platform
HAL.register('dell_g5_5090', DELL_G5_5090)
