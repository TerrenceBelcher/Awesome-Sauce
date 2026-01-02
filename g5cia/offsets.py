"""Dell G5 5090 BIOS offset definitions."""

from typing import Dict, Any

# Dell G5 5090 Setup variable offsets
# Format: 'name': (offset, size, description)

OFFSETS: Dict[str, tuple[int, int, str]] = {
    # Lock bits
    'CfgLk': (0x43, 1, 'CFG Lock (MSR 0xE2)'),
    'OcLk': (0x44, 1, 'Overclocking Lock'),
    'PlLk': (0x5E, 1, 'Power Limit Lock'),
    'BiosLk': (0x5F, 1, 'BIOS Interface Lock'),
    'PkgLk': (0x60, 1, 'Package Config Lock'),
    'TdpLk': (0x6B, 1, 'TDP Lock'),
    'SmmLk': (0x109, 1, 'SMM BIOS Write Protect'),
    'FlshLk': (0x10A, 1, 'Flash Lock'),
    
    # Power Limits
    'Pl1En': (0x64, 1, 'PL1 Enable'),
    'Pl2En': (0x65, 1, 'PL2 Enable'),
    'Pl1L': (0x66, 1, 'PL1 Low Byte'),
    'Pl1H': (0x67, 1, 'PL1 High Byte'),
    'Pl2L': (0x68, 1, 'PL2 Low Byte'),
    'Pl2H': (0x69, 1, 'PL2 High Byte'),
    'Pl3L': (0x6C, 1, 'PL3 Low Byte'),
    'Pl3H': (0x6D, 1, 'PL3 High Byte'),
    'Pl4L': (0x6E, 1, 'PL4 Low Byte'),
    'Pl4H': (0x6F, 1, 'PL4 High Byte'),
    'Tau': (0x6A, 1, 'Turbo Time Window'),
    
    # Voltage Offsets (signed 16-bit in 1/1024V units)
    'VcOL': (0x70, 1, 'Vcore Offset Low'),
    'VcOH': (0x71, 1, 'Vcore Offset High'),
    'VcPL': (0x72, 1, 'Vcore Prefix Low'),
    'VcPH': (0x73, 1, 'Vcore Prefix High'),
    'RgOL': (0x74, 1, 'Ring Offset Low'),
    'RgOH': (0x75, 1, 'Ring Offset High'),
    'RgPL': (0x76, 1, 'Ring Prefix Low'),
    'RgPH': (0x77, 1, 'Ring Prefix High'),
    'SaOL': (0x78, 1, 'SA Offset Low'),
    'SaOH': (0x79, 1, 'SA Offset High'),
    'SaPL': (0x7A, 1, 'SA Prefix Low'),
    'SaPH': (0x7B, 1, 'SA Prefix High'),
    'IoOL': (0x7C, 1, 'IO Offset Low'),
    'IoOH': (0x7D, 1, 'IO Offset High'),
    'IoPL': (0x7E, 1, 'IO Prefix Low'),
    'IoPH': (0x7F, 1, 'IO Prefix High'),
    
    # Current Limits
    'IccL': (0x80, 1, 'ICC Max Low'),
    'IccH': (0x81, 1, 'ICC Max High'),
    'AcLL': (0x82, 1, 'AC Loadline Low'),
    'DcLL': (0x83, 1, 'DC Loadline Low'),
    
    # C-States
    'CSt': (0x90, 1, 'C-States Enable'),
    'C1E': (0x91, 1, 'Enhanced C1 State'),
    'PkgC': (0x92, 1, 'Package C-State'),
    'C3': (0x93, 1, 'C3 State'),
    'C6': (0x94, 1, 'C6 State'),
    'C7': (0x95, 1, 'C7 State'),
    'C8': (0x96, 1, 'C8 State'),
    'C9': (0x97, 1, 'C9 State'),
    'C10': (0x98, 1, 'C10 State'),
    'EEP': (0x99, 1, 'Energy Efficient P-State'),
    'Race': (0x9A, 1, 'Race To Halt'),
    
    # Turbo
    'Trbo': (0xA0, 1, 'Turbo Mode'),
    'TrMd': (0xA1, 1, 'Turbo Mode Select'),
    'R1': (0xA2, 1, 'Turbo Ratio 1-Core'),
    'R2': (0xA3, 1, 'Turbo Ratio 2-Core'),
    'R3': (0xA4, 1, 'Turbo Ratio 3-Core'),
    'R4': (0xA5, 1, 'Turbo Ratio 4-Core'),
    'R5': (0xA6, 1, 'Turbo Ratio 5-Core'),
    'R6': (0xA7, 1, 'Turbo Ratio 6-Core'),
    'RgH': (0xA8, 1, 'Ring Max Ratio'),
    'RgL': (0xA9, 1, 'Ring Min Ratio'),
    'HWP': (0xAA, 1, 'Hardware P-States'),
    'EPP': (0xAB, 1, 'Energy Performance Preference'),
    'HDC': (0xAC, 1, 'Hardware Duty Cycling'),
    'SSI': (0xAD, 1, 'Speed Shift Interrupt'),
    
    # Memory - Primary Timings
    'Xmp': (0xB0, 1, 'XMP Profile'),
    'MFreq': (0xB1, 2, 'Memory Frequency'),
    'tCL': (0xB3, 1, 'CAS Latency'),
    'tRCD': (0xB4, 1, 'RAS to CAS Delay'),
    'tRP': (0xB5, 1, 'Row Precharge'),
    'tRAS': (0xB6, 1, 'Row Active Time'),
    'tFAW': (0xB7, 1, 'Four Activate Window'),
    'tRDWR': (0xB8, 1, 'Read to Write Delay'),
    'tWRRD': (0xB9, 1, 'Write to Read Delay'),
    'tRFC': (0xBA, 2, 'Refresh Cycle Time'),
    'tREFI': (0xBC, 2, 'Refresh Interval'),
    'tCWL': (0xBE, 1, 'CAS Write Latency'),
    
    # Memory - Advanced
    'RttNom': (0xC0, 1, 'RTT Nominal'),
    'RttWr': (0xC1, 1, 'RTT Write'),
    'RttPrk': (0xC2, 1, 'RTT Park'),
    'OdtEn': (0xC3, 1, 'ODT Enable'),
    'DrvStr': (0xC4, 1, 'Drive Strength'),
    
    # PCIe
    'A4G': (0xD0, 1, 'Above 4G Decoding'),
    'RBar': (0xD1, 1, 'Resizable BAR'),
    'CSM': (0xD2, 1, 'Compatibility Support Module'),
    'ASPM': (0xD3, 1, 'Active State Power Management'),
    'L1Sub': (0xD4, 1, 'L1 Substates'),
    'Acs': (0xD5, 1, 'Access Control Services'),
    'MaxPL': (0xD6, 1, 'Max Payload Size'),
    'MaxRR': (0xD7, 1, 'Max Read Request'),
    'DmiGen': (0xD8, 1, 'DMI Gen'),
    'DmiAspm': (0xD9, 1, 'DMI ASPM'),
    
    # Thermal
    'FanCtl': (0xE0, 1, 'Fan Control'),
    'FanMd': (0xE1, 1, 'Fan Mode'),
    'F1': (0xE2, 1, 'Fan 1 Speed %'),
    'F2': (0xE3, 1, 'Fan 2 Speed %'),
    'F3': (0xE4, 1, 'Fan 3 Speed %'),
    'F4': (0xE5, 1, 'Fan 4 Speed %'),
    'F5': (0xE6, 1, 'Fan 5 Speed %'),
    'F6': (0xE7, 1, 'Fan 6 Speed %'),
    'T1': (0xE8, 1, 'Temp Threshold 1 °C'),
    'T2': (0xE9, 1, 'Temp Threshold 2 °C'),
    'T3': (0xEA, 1, 'Temp Threshold 3 °C'),
    'T4': (0xEB, 1, 'Temp Threshold 4 °C'),
    'T5': (0xEC, 1, 'Temp Threshold 5 °C'),
    'T6': (0xED, 1, 'Temp Threshold 6 °C'),
    'FRamp': (0xEE, 1, 'Fan Ramp Rate'),
    'FHyst': (0xEF, 1, 'Fan Hysteresis'),
    'FMin': (0xF0, 1, 'Fan Min Speed %'),
    'FMax': (0xF1, 1, 'Fan Max Speed %'),
    'TjOff': (0xF2, 1, 'TjMax Offset'),
    
    # Features
    'iGPU': (0x100, 1, 'Integrated GPU'),
    'VtD': (0x101, 1, 'VT-d'),
    'VtX': (0x102, 1, 'VT-x'),
    'Sgx': (0x103, 1, 'Software Guard Extensions'),
    'TpmEn': (0x104, 1, 'TPM Device'),
    'Ptt': (0x105, 1, 'Platform Trust Technology'),
    'MeEn': (0x106, 1, 'Management Engine'),
    'Hap': (0x107, 1, 'High Assurance Platform (ME Disable)'),
    'SecBoot': (0x108, 1, 'Secure Boot'),
}


def get_offset(name: str) -> tuple[int, int]:
    """Get offset and size for a setting by name."""
    if name not in OFFSETS:
        raise KeyError(f"Unknown offset: {name}")
    return OFFSETS[name][0], OFFSETS[name][1]


def get_description(name: str) -> str:
    """Get description for a setting by name."""
    if name not in OFFSETS:
        return "Unknown"
    return OFFSETS[name][2]


def list_offsets() -> list[tuple[str, int, int, str]]:
    """List all offsets with details."""
    return [(name, off, sz, desc) for name, (off, sz, desc) in OFFSETS.items()]
