"""Dell XPS 8940 platform profile."""

from .hal import HAL, PlatformInfo


# Dell XPS 8940 (enthusiast desktop, 10th/11th gen)
DELL_XPS_8940 = PlatformInfo(
    name="Dell XPS 8940",
    codename="XPS 8940",
    manufacturer="Dell",
    pch="Z490/Z590",  # Enthusiast chipsets
    
    # Supported CPUIDs (10th/11th gen Intel Core)
    supported_cpuids=[
        0xA0655,  # i9-10900K (10th gen)
        0xA0653,  # i7-10700K
        0xA0671,  # i9-11900K (11th gen)
        0xA0670,  # i7-11700K
    ],
    
    # VRM limits (better VRM for K-series CPUs)
    vrm_sustained=125,
    vrm_burst=150,
    vrm_max_safe=175,
    
    # Static offsets (estimated, would need verification)
    static_offsets={
        'CfgLk': (0x43, 1),
        'OcLk': (0x44, 1),
        'PlLk': (0x5E, 1),
        'BiosLk': (0x5F, 1),
        'Pl1L': (0x66, 1),
        'Pl1H': (0x67, 1),
        'Pl2L': (0x68, 1),
        'Pl2H': (0x69, 1),
        'Tau': (0x6A, 1),
        'VcOL': (0x70, 1),
        'VcOH': (0x71, 1),
        'RgOL': (0x74, 1),
        'RgOH': (0x75, 1),
        'SaOL': (0x78, 1),
        'SaOH': (0x79, 1),
        'IoOL': (0x7C, 1),
        'IoOH': (0x7D, 1),
        'A4G': (0xD0, 1),
        'RBar': (0xD1, 1),
        'MeEn': (0x106, 1),
        'Hap': (0x107, 1),
    },
    
    # Known BIOS versions (placeholder)
    bios_versions=[
        '2.0.0', '2.1.0', '2.2.0', '2.3.0',
    ],
    
    # Detection signatures
    signatures=[
        b'Dell Inc.\x00',
        b'XPS 8940\x00',
    ],
    
    # Feature support (Z-series chipset has full support)
    supports_rebar=True,
    supports_above_4g=True,
    supports_me_disable=True,
)


# Register platform
HAL.register('dell_xps_8940', DELL_XPS_8940)
