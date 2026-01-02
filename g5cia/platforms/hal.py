"""Hardware Abstraction Layer for multi-platform support."""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class PlatformInfo:
    """Platform-specific information and constraints."""
    
    # Identity
    name: str
    codename: str
    manufacturer: str
    
    # Hardware
    pch: str
    supported_cpuids: List[int] = field(default_factory=list)
    
    # Power limits (VRM constraints)
    vrm_sustained: int = 65  # PL1 limit in watts
    vrm_burst: int = 90      # PL2 limit in watts
    vrm_max_safe: int = 100  # Absolute maximum recommended
    
    # Static offsets (fallback when IFR parsing fails)
    static_offsets: Dict[str, tuple[int, int]] = field(default_factory=dict)
    
    # Known BIOS versions
    bios_versions: List[str] = field(default_factory=list)
    
    # Signatures for detection
    signatures: List[bytes] = field(default_factory=list)
    
    # Feature support
    supports_rebar: bool = True
    supports_above_4g: bool = True
    supports_me_disable: bool = True
    
    def validate_power_limits(self, pl1: Optional[int], pl2: Optional[int]) -> List[str]:
        """Validate power limits against VRM constraints.
        
        Args:
            pl1: PL1 power limit in watts
            pl2: PL2 power limit in watts
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        if pl1 and pl1 > self.vrm_sustained:
            warnings.append(
                f"⚠️  PL1 {pl1}W exceeds {self.name} VRM sustained spec ({self.vrm_sustained}W)"
            )
        
        if pl2 and pl2 > self.vrm_burst:
            warnings.append(
                f"⚠️  PL2 {pl2}W exceeds {self.name} VRM burst spec ({self.vrm_burst}W)"
            )
        
        if pl1 and pl1 > self.vrm_max_safe:
            warnings.append(
                f"🔥 PL1 {pl1}W exceeds absolute safe maximum ({self.vrm_max_safe}W) - VRM damage risk!"
            )
        
        if pl2 and pl2 > self.vrm_max_safe + 20:
            warnings.append(
                f"🔥 PL2 {pl2}W is dangerously high - VRM damage risk!"
            )
        
        return warnings


class HAL:
    """Hardware Abstraction Layer registry."""
    
    _platforms: Dict[str, PlatformInfo] = {}
    
    @classmethod
    def register(cls, platform_id: str, platform: PlatformInfo) -> None:
        """Register a platform.
        
        Args:
            platform_id: Unique platform identifier
            platform: Platform information
        """
        cls._platforms[platform_id] = platform
        log.debug(f"Registered platform: {platform_id} ({platform.name})")
    
    @classmethod
    def get_platform(cls, platform_id: str) -> Optional[PlatformInfo]:
        """Get platform by ID.
        
        Args:
            platform_id: Platform identifier
            
        Returns:
            PlatformInfo or None if not found
        """
        return cls._platforms.get(platform_id)
    
    @classmethod
    def list_platforms(cls) -> List[str]:
        """List all registered platform IDs.
        
        Returns:
            List of platform identifiers
        """
        return list(cls._platforms.keys())
    
    @classmethod
    def detect_platform(cls, bios_data: bytes) -> Optional[PlatformInfo]:
        """Auto-detect platform from BIOS data.
        
        Args:
            bios_data: Raw BIOS data
            
        Returns:
            Detected PlatformInfo or None
        """
        # Try signature matching
        for platform_id, platform in cls._platforms.items():
            for signature in platform.signatures:
                if signature in bios_data:
                    log.info(f"Detected platform: {platform.name}")
                    return platform
        
        log.warning("Could not detect platform from BIOS data")
        return None
    
    @classmethod
    def validate_config(cls, platform: PlatformInfo, config: dict) -> List[str]:
        """Validate configuration against platform constraints.
        
        Args:
            platform: Platform info
            config: Configuration dictionary
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Validate power limits
        pl1 = config.get('pl1')
        pl2 = config.get('pl2')
        warnings.extend(platform.validate_power_limits(pl1, pl2))
        
        # Check feature support
        if config.get('resizable_bar') and not platform.supports_rebar:
            warnings.append(f"⚠️  {platform.name} may not support Resizable BAR")
        
        if config.get('above_4g') and not platform.supports_above_4g:
            warnings.append(f"⚠️  {platform.name} may not support Above 4G Decoding")
        
        if config.get('me_disable') and not platform.supports_me_disable:
            warnings.append(f"⚠️  {platform.name} may not support ME disable")
        
        return warnings
    
    @classmethod
    def print_platforms(cls) -> None:
        """Print all registered platforms."""
        print("\n" + "="*70)
        print("SUPPORTED PLATFORMS")
        print("="*70)
        
        if not cls._platforms:
            print("No platforms registered")
        else:
            for platform_id, platform in cls._platforms.items():
                print(f"\n[{platform_id}]")
                print(f"  Name: {platform.name}")
                print(f"  Codename: {platform.codename}")
                print(f"  Manufacturer: {platform.manufacturer}")
                print(f"  PCH: {platform.pch}")
                print(f"  VRM Limits: PL1={platform.vrm_sustained}W, PL2={platform.vrm_burst}W")
                
                if platform.bios_versions:
                    versions = ', '.join(platform.bios_versions[:3])
                    if len(platform.bios_versions) > 3:
                        versions += f", ... ({len(platform.bios_versions)} total)"
                    print(f"  Known BIOS Versions: {versions}")
        
        print("="*70 + "\n")
