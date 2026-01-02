"""Main orchestration engine for BIOS patching workflow."""

import logging
import shutil
from typing import Optional
from pathlib import Path
from dataclasses import dataclass

from .image import ImageParser
from .security import SecurityAnalyzer, find_microcode_updates
from .patcher import Patcher
from .config import BIOSConfig
from .hw import detect_hardware, check_cpu_compat
from .logo import LogoManager, COLORS, GRADIENTS
from .rebar import ReBarInjector

log = logging.getLogger(__name__)


@dataclass
class EngineStats:
    """Statistics from patching operation."""
    input_size: int = 0
    output_size: int = 0
    volumes_found: int = 0
    patches_applied: int = 0
    boot_guard: bool = False
    me_found: bool = False
    safe_to_flash: bool = True
    warnings: list = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class PatchEngine:
    """Main BIOS patching engine."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stats = EngineStats()
        
        # Components
        self.parser: Optional[ImageParser] = None
        self.security: Optional[SecurityAnalyzer] = None
        self.patcher: Optional[Patcher] = None
        self.logo_mgr: Optional[LogoManager] = None
        
        # Data
        self.data: Optional[bytearray] = None
    
    def load(self, image_path: str) -> bool:
        """Load and parse firmware image."""
        log.info(f"Loading firmware image: {image_path}")
        
        try:
            raw_data = Path(image_path).read_bytes()
            self.data = bytearray(raw_data)
            self.stats.input_size = len(self.data)
            
            log.info(f"Image loaded: {len(self.data)} bytes")
        except Exception as e:
            log.error(f"Failed to load image: {e}")
            return False
        
        # Parse firmware structure
        self.parser = ImageParser(bytes(self.data))
        if not self.parser.parse():
            log.error("Failed to parse firmware structure")
            return False
        
        self.stats.volumes_found = len(self.parser.volumes)
        log.info(f"Parsed {self.stats.volumes_found} firmware volumes")
        
        # Initialize components
        self.patcher = Patcher(bytes(self.data))
        self.logo_mgr = LogoManager(self.parser)
        
        # Set Setup base offset if found
        if self.parser.setup_offset:
            self.patcher.set_setup_base(self.parser.setup_offset)
        else:
            log.warning("Setup data not found - Setup variable patching disabled")
        
        return True
    
    def preflight(self, force: bool = False) -> bool:
        """Run preflight safety checks.
        
        Returns:
            True if safe to proceed
        """
        log.info("Running preflight checks...")
        
        # Security analysis
        self.security = SecurityAnalyzer(bytes(self.data))
        status = self.security.analyze()
        
        self.stats.boot_guard = status.boot_guard_enabled
        self.stats.me_found = status.me_region_found
        self.stats.safe_to_flash = status.safe_to_flash
        self.stats.warnings.extend(status.warnings)
        
        # Hardware detection
        hw = detect_hardware()
        log.info(f"Detected hardware: {hw.cpu_model or 'Unknown CPU'}")
        
        if hw.cpu_model:
            compat, msg = check_cpu_compat(hw.cpu_model)
            log.info(msg)
            if not compat:
                self.stats.warnings.append(msg)
        
        # Print warnings
        if self.stats.warnings:
            log.warning("\n" + "="*70)
            log.warning("PREFLIGHT WARNINGS:")
            for warning in self.stats.warnings:
                log.warning(f"  • {warning}")
            log.warning("="*70 + "\n")
        
        # Hard fail on critical issues
        if not status.safe_to_flash and not force:
            log.error("PREFLIGHT FAILED: Critical security blocks detected")
            log.error("Use --force to override (DANGER: May brick system!)")
            return False
        
        if not status.safe_to_flash and force:
            log.warning("⚠️  FORCE MODE: Bypassing safety checks - YOU HAVE BEEN WARNED!")
        
        log.info("✓ Preflight checks passed")
        return True
    
    def apply_config(self, config: BIOSConfig) -> bool:
        """Apply BIOS configuration.
        
        Args:
            config: Configuration to apply
        
        Returns:
            True if successful
        """
        if not self.patcher or not self.patcher.setup_base:
            log.error("Setup base not available - cannot apply config")
            return False
        
        log.info(f"Applying preset: {config.preset}")
        
        # Unlock
        if config.cfg_lock == 0:
            self.patcher.unlock_all()
        
        # Power limits
        if config.pl1 is not None:
            if config.pl1 > 95:
                log.warning(f"⚠️  PL1 {config.pl1}W exceeds Dell G5 5090 VRM spec (95W)")
            self.patcher.set_power_limit('Pl1', config.pl1)
            self.patcher.patch_setup_offset('Pl1En', 1)
        
        if config.pl2 is not None:
            if config.pl2 > 115:
                log.warning(f"⚠️  PL2 {config.pl2}W exceeds Dell G5 5090 VRM spec (115W)")
            self.patcher.set_power_limit('Pl2', config.pl2)
            self.patcher.patch_setup_offset('Pl2En', 1)
        
        if config.pl3 is not None:
            self.patcher.set_power_limit('Pl3', config.pl3)
        
        if config.pl4 is not None:
            self.patcher.set_power_limit('Pl4', config.pl4)
        
        if config.tau is not None:
            self.patcher.patch_setup_offset('Tau', config.tau)
        
        # Voltage offsets
        if config.vcore_offset is not None:
            self.patcher.set_voltage_offset('Vc', config.vcore_offset)
        
        if config.ring_offset is not None:
            self.patcher.set_voltage_offset('Rg', config.ring_offset)
        
        if config.sa_offset is not None:
            self.patcher.set_voltage_offset('Sa', config.sa_offset)
        
        if config.io_offset is not None:
            self.patcher.set_voltage_offset('Io', config.io_offset)
        
        # Turbo ratios
        if config.turbo_1c is not None:
            self.patcher.patch_setup_offset('R1', config.turbo_1c)
        if config.turbo_2c is not None:
            self.patcher.patch_setup_offset('R2', config.turbo_2c)
        if config.turbo_3c is not None:
            self.patcher.patch_setup_offset('R3', config.turbo_3c)
        if config.turbo_4c is not None:
            self.patcher.patch_setup_offset('R4', config.turbo_4c)
        if config.turbo_5c is not None:
            self.patcher.patch_setup_offset('R5', config.turbo_5c)
        if config.turbo_6c is not None:
            self.patcher.patch_setup_offset('R6', config.turbo_6c)
        
        # C-States
        if config.c_states is not None:
            self.patcher.patch_setup_offset('CSt', config.c_states)
        if config.c1e is not None:
            self.patcher.patch_setup_offset('C1E', config.c1e)
        if config.pkg_c_state is not None:
            self.patcher.patch_setup_offset('PkgC', config.pkg_c_state)
        
        # PCIe
        if config.above_4g is not None:
            self.patcher.patch_setup_offset('A4G', config.above_4g)
        if config.resizable_bar is not None:
            self.patcher.patch_setup_offset('RBar', config.resizable_bar)
        
        # ME disable
        if config.me_disable is not None and config.me_disable == 1:
            log.info("Setting HAP bit to disable ME")
            self.patcher.set_hap_bit(True)
        
        self.stats.patches_applied = len(self.patcher.patches)
        log.info(f"✓ Applied {self.stats.patches_applied} patches")
        
        return True
    
    def inject_rebar_driver(self, driver_path: Optional[str] = None, 
                           force: bool = False) -> bool:
        """Inject ReBAR driver."""
        if not self.parser:
            log.error("Image not loaded")
            return False
        
        injector = ReBarInjector(self.parser)
        
        if not injector.download_driver(driver_path):
            return False
        
        return injector.inject(self.data, force)
    
    def save(self, output_path: str, atomic: bool = True) -> bool:
        """Save patched firmware.
        
        Args:
            output_path: Output file path
            atomic: Use atomic save (write to temp, verify, rename)
        
        Returns:
            True if successful
        """
        if not self.data:
            log.error("No data to save")
            return False
        
        # Update patcher data
        if self.patcher:
            self.data = bytearray(self.patcher.get_data())
        
        self.stats.output_size = len(self.data)
        
        if atomic:
            # Atomic save
            temp_path = output_path + '.tmp'
            
            log.info(f"Writing to temporary file: {temp_path}")
            Path(temp_path).write_bytes(self.data)
            
            # Verify by parsing
            log.info("Verifying output...")
            verify_parser = ImageParser(bytes(self.data))
            if not verify_parser.parse():
                log.error("Verification failed - output may be corrupted")
                Path(temp_path).unlink()
                return False
            
            # Rename to final name
            log.info(f"Moving to final location: {output_path}")
            shutil.move(temp_path, output_path)
        else:
            # Direct save
            Path(output_path).write_bytes(self.data)
        
        log.info(f"✓ Saved to {output_path} ({len(self.data)} bytes)")
        return True
    
    def print_summary(self) -> None:
        """Print operation summary."""
        print("\n" + "="*70)
        print("OPERATION SUMMARY")
        print("="*70)
        print(f"Input size:       {self.stats.input_size:,} bytes")
        print(f"Output size:      {self.stats.output_size:,} bytes")
        print(f"Volumes found:    {self.stats.volumes_found}")
        print(f"Patches applied:  {self.stats.patches_applied}")
        print(f"Boot Guard:       {'Yes' if self.stats.boot_guard else 'No'}")
        print(f"ME region:        {'Found' if self.stats.me_found else 'Not found'}")
        print(f"Safe to flash:    {'✓ Yes' if self.stats.safe_to_flash else '✗ NO - USE CAUTION'}")
        
        if self.stats.warnings:
            print(f"\nWarnings: {len(self.stats.warnings)}")
            for warning in self.stats.warnings[:5]:  # Show first 5
                print(f"  • {warning}")
        
        print("="*70 + "\n")
        
        if self.patcher:
            print(self.patcher.get_patch_summary())
