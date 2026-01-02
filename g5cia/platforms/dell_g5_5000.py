"""Dell G5 5000 platform profile."""

from .hal import HAL, PlatformInfo


# Dell G5 5000 platform (newer generation)
DELL_G5_5000 = PlatformInfo(
    name="Dell G5 5000",
    codename="Inspiron 5000",
    manufacturer="Dell",
    pch="B560/H570",  # 11th gen chipsets
    
    # Supported CPUIDs (11th gen Intel Core - Rocket Lake)
    supported_cpuids=[
        0xA0671,  # i9-11900
        0xA0670,  # i7-11700
        0xA0672,  # i5-11600/11400
        0xA0673,  # i3-11320
    ],
    
    # VRM limits (slightly better VRM than 5090)
    vrm_sustained=105,
    vrm_burst=125,
    vrm_max_safe=135,
    
    # Static offsets (placeholder - would need real BIOS analysis)
    # These are estimated based on G5 5090, may differ
    static_offsets={
        'CfgLk': (0x43, 1),
        'OcLk': (0x44, 1),
        'PlLk': (0x5E, 1),
        'BiosLk': (0x5F, 1),
        'Pl1L': (0x66, 1),
        'Pl1H': (0x67, 1),
        'Pl2L': (0x68, 1),
        'Pl2H': (0x69, 1),
        'VcOL': (0x70, 1),
        'VcOH': (0x71, 1),
        'RgOL': (0x74, 1),
        'RgOH': (0x75, 1),
        'A4G': (0xD0, 1),
        'RBar': (0xD1, 1),
        'Hap': (0x107, 1),
    },
    
    # Known BIOS versions (placeholder)
    bios_versions=[
        '1.0.0', '1.1.0', '1.2.0',
    ],
    
    # Detection signatures
    signatures=[
        b'Dell Inc.\x00',
        b'G5 5000\x00',
        b'Inspiron 5000\x00',
    ],
    
    # Feature support (11th gen has better support)
    supports_rebar=True,
    supports_above_4g=True,
    supports_me_disable=True,
)


# Register platform
HAL.register('dell_g5_5000', DELL_G5_5000)
