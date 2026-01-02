"""Configuration dataclasses and presets."""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import json


@dataclass
class MemoryTimings:
    """Memory timing configuration."""
    xmp: int = 0  # 0=disabled, 1=profile1, 2=profile2
    freq: Optional[int] = None  # MHz
    tCL: Optional[int] = None
    tRCD: Optional[int] = None
    tRP: Optional[int] = None
    tRAS: Optional[int] = None
    tFAW: Optional[int] = None
    tRDWR: Optional[int] = None
    tWRRD: Optional[int] = None
    tRFC: Optional[int] = None
    tREFI: Optional[int] = None
    tCWL: Optional[int] = None
    rtt_nom: Optional[int] = None
    rtt_wr: Optional[int] = None
    rtt_park: Optional[int] = None


@dataclass
class FanCurve:
    """Fan curve configuration."""
    mode: int = 0  # 0=auto, 1=manual, 2=custom
    speeds: list[int] = field(default_factory=lambda: [30, 50, 70, 85, 95, 100])
    temps: list[int] = field(default_factory=lambda: [40, 50, 60, 70, 80, 90])
    ramp_rate: int = 5
    hysteresis: int = 3
    min_speed: int = 20
    max_speed: int = 100


@dataclass
class BIOSConfig:
    """Complete BIOS configuration."""
    # Preset name
    preset: str = "stock"
    
    # Locks (0=unlocked, 1=locked)
    cfg_lock: int = 0
    oc_lock: int = 0
    
    # Power Limits (watts)
    pl1: Optional[int] = None
    pl2: Optional[int] = None
    pl3: Optional[int] = None
    pl4: Optional[int] = None
    tau: Optional[int] = None  # seconds
    
    # Voltage Offsets (mV, negative = undervolt)
    vcore_offset: Optional[int] = None
    ring_offset: Optional[int] = None
    sa_offset: Optional[int] = None
    io_offset: Optional[int] = None
    
    # Turbo Ratios (multiplier * 10)
    turbo_1c: Optional[int] = None
    turbo_2c: Optional[int] = None
    turbo_3c: Optional[int] = None
    turbo_4c: Optional[int] = None
    turbo_5c: Optional[int] = None
    turbo_6c: Optional[int] = None
    
    # C-States (0=disabled, 1=enabled)
    c_states: Optional[int] = None
    c1e: Optional[int] = None
    pkg_c_state: Optional[int] = None
    
    # Memory
    memory: MemoryTimings = field(default_factory=MemoryTimings)
    
    # PCIe
    above_4g: Optional[int] = None
    resizable_bar: Optional[int] = None
    
    # Thermal
    fan_curve: FanCurve = field(default_factory=FanCurve)
    
    # Features
    me_disable: Optional[int] = None  # HAP bit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BIOSConfig':
        """Create from dictionary."""
        # Handle nested dataclasses
        if 'memory' in data and isinstance(data['memory'], dict):
            data['memory'] = MemoryTimings(**data['memory'])
        if 'fan_curve' in data and isinstance(data['fan_curve'], dict):
            data['fan_curve'] = FanCurve(**data['fan_curve'])
        return cls(**data)
    
    def save(self, path: str) -> None:
        """Save configuration to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> 'BIOSConfig':
        """Load configuration from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


# Preset Configurations
PRESETS: Dict[str, BIOSConfig] = {
    'stock': BIOSConfig(
        preset='stock',
        cfg_lock=1,
        oc_lock=1,
    ),
    
    'balanced': BIOSConfig(
        preset='balanced',
        cfg_lock=0,
        oc_lock=0,
        pl1=65,
        pl2=90,
        tau=28,
        vcore_offset=-25,
        ring_offset=-25,
        c_states=1,
        c1e=1,
        pkg_c_state=7,
    ),
    
    'perf': BIOSConfig(
        preset='perf',
        cfg_lock=0,
        oc_lock=0,
        pl1=85,
        pl2=105,
        tau=56,
        vcore_offset=-15,
        ring_offset=-15,
        c_states=1,
        c1e=1,
        pkg_c_state=3,
    ),
    
    'gaming': BIOSConfig(
        preset='gaming',
        cfg_lock=0,
        oc_lock=0,
        pl1=80,
        pl2=100,
        pl3=110,
        tau=40,
        vcore_offset=-20,
        ring_offset=-20,
        c_states=1,
        c1e=1,
        pkg_c_state=3,
        above_4g=1,
        resizable_bar=1,
        fan_curve=FanCurve(
            mode=1,
            speeds=[35, 55, 75, 90, 100, 100],
            temps=[45, 55, 65, 75, 85, 95],
        ),
    ),
    
    'max': BIOSConfig(
        preset='max',
        cfg_lock=0,
        oc_lock=0,
        pl1=95,  # WARNING: Above Dell VRM spec
        pl2=115,  # WARNING: Above Dell VRM spec
        pl3=125,
        pl4=135,
        tau=128,
        vcore_offset=-10,
        ring_offset=-10,
        c_states=0,
        c1e=0,
        pkg_c_state=0,
        above_4g=1,
        resizable_bar=1,
        fan_curve=FanCurve(
            mode=1,
            speeds=[40, 60, 80, 95, 100, 100],
            temps=[40, 50, 60, 70, 80, 90],
            min_speed=30,
        ),
    ),
    
    'silent': BIOSConfig(
        preset='silent',
        cfg_lock=0,
        oc_lock=0,
        pl1=45,
        pl2=65,
        tau=20,
        vcore_offset=-40,
        ring_offset=-40,
        c_states=1,
        c1e=1,
        pkg_c_state=10,
        fan_curve=FanCurve(
            mode=1,
            speeds=[20, 30, 45, 60, 75, 90],
            temps=[50, 60, 70, 80, 90, 100],
            min_speed=15,
            max_speed=80,
        ),
    ),
    
    'uv': BIOSConfig(
        preset='uv',
        cfg_lock=0,
        oc_lock=0,
        vcore_offset=-75,
        ring_offset=-60,
        sa_offset=-50,
        io_offset=-50,
    ),
    
    'bare': BIOSConfig(
        preset='bare',
        cfg_lock=0,
        oc_lock=0,
        pl1=None,
        pl2=None,
        me_disable=1,
    ),
}


def get_preset(name: str) -> BIOSConfig:
    """Get preset configuration by name."""
    if name not in PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {', '.join(PRESETS.keys())}")
    return PRESETS[name]


def list_presets() -> list[str]:
    """List available preset names."""
    return list(PRESETS.keys())
