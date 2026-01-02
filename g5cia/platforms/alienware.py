"""Alienware Aurora R10 platform profile."""

from .hal import HAL, PlatformInfo


# Alienware Aurora R10 (AMD Ryzen platform)
ALIENWARE_AURORA_R10 = PlatformInfo(
    name="Alienware Aurora R10",
    codename="Aurora R10",
    manufacturer="Dell/Alienware",
    pch="AMD X570",  # AMD chipset
    
    # Supported CPUIDs (AMD Ryzen 3000/5000 series)
    # Note: AMD uses different CPUID format
    supported_cpuids=[
        0x870F10,  # Ryzen 9 5950X/5900X
        0x870F00,  # Ryzen 7 5800X
        0x830F10,  # Ryzen 9 3950X/3900X
        0x830F00,  # Ryzen 7 3800X/3700X
    ],
    
    # VRM limits (Aurora R10 has robust VRM for high-end Ryzen)
    vrm_sustained=140,
    vrm_burst=170,
    vrm_max_safe=200,
    
    # Static offsets (AMD BIOS - different structure)
    # These are placeholders - AMD BIOS has very different layout
    static_offsets={
        # AMD doesn't use same lock mechanism as Intel
        # This would need AMD-specific offset discovery
        'CfgLk': (0x50, 1),  # Estimated
        'OcLk': (0x51, 1),   # Estimated
        'PptL': (0x70, 2),   # PPT (Package Power Tracking)
        'TdcL': (0x72, 2),   # TDC (Thermal Design Current)
        'EdcL': (0x74, 2),   # EDC (Electrical Design Current)
        'A4G': (0xD0, 1),    # Same as Intel platforms
        'RBar': (0xD1, 1),   # Same as Intel platforms
    },
    
    # Known BIOS versions
    bios_versions=[
        '1.0.0', '1.0.1', '1.0.2', '1.0.3', '1.0.4',
    ],
    
    # Detection signatures
    signatures=[
        b'Alienware\x00',
        b'Aurora R10\x00',
        b'Dell Inc.\x00Alienware',
    ],
    
    # Feature support
    supports_rebar=True,
    supports_above_4g=True,
    supports_me_disable=False,  # No ME on AMD platforms
)


# Register platform
HAL.register('alienware_aurora_r10', ALIENWARE_AURORA_R10)
