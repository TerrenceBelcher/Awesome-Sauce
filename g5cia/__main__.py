"""Command-line interface for G5 CIA Ultimate."""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

from . import __version__
from .nvram import NVRAMAccess, print_nvram_report
from .config import BIOSConfig, get_preset, list_presets
from .engine import PatchEngine
from .logo import LogoManager, COLORS, GRADIENTS


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    
    fmt = '%(levelname)-8s %(message)s' if not verbose else '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt='%H:%M:%S'
    )


def cmd_nvram_report(args) -> int:
    """NVRAM report command."""
    print_nvram_report()
    return 0


def cmd_nvram_backup(args) -> int:
    """Backup NVRAM Setup variable."""
    nvram = NVRAMAccess()
    if not nvram.can_access:
        logging.error("No NVRAM access - need admin/root privileges")
        return 1
    
    if nvram.backup_setup(args.backup_file):
        logging.info(f"✓ Setup backed up to {args.backup_file}")
        return 0
    else:
        return 1


def cmd_nvram_restore(args) -> int:
    """Restore NVRAM Setup variable."""
    nvram = NVRAMAccess()
    if not nvram.can_access:
        logging.error("No NVRAM access - need admin/root privileges")
        return 1
    
    if nvram.restore_setup(args.restore_file):
        logging.info(f"✓ Setup restored from {args.restore_file}")
        return 0
    else:
        return 1


def cmd_nvram_unlock(args) -> int:
    """Unlock via NVRAM (instant, no flash)."""
    from .runtime.nvram_tool import NVRAMUnlocker
    
    unlocker = NVRAMUnlocker()
    
    dry = getattr(args, 'dry', False)
    
    if dry:
        logging.info("Running in DRY RUN mode - no changes will be made")
    
    logging.info("Unlocking BIOS settings via NVRAM...")
    results = unlocker.nv_unlock(dry=dry)
    
    # Print results
    print("\n" + "="*70)
    print("NVRAM UNLOCK RESULTS")
    print("="*70)
    
    success_count = 0
    for setting_name, success, message in results:
        status = "✓" if success else "✗"
        print(f"{status} {setting_name:25s} {message}")
        if success:
            success_count += 1
    
    print("="*70)
    print(f"Successful: {success_count}/{len(results)}")
    print("="*70 + "\n")
    
    if not dry:
        print("⚠️  IMPORTANT: Reboot for changes to take effect")
        print("    To restore: CMOS clear or use --nv-restore")
    
    return 0 if success_count > 0 else 1


def cmd_nvram_apply(args) -> int:
    """Apply preset via NVRAM."""
    logging.info(f"NVRAM apply preset '{args.preset}' not yet implemented")
    return 1


def cmd_patch_bios(args) -> int:
    """Patch BIOS image."""
    if not args.input:
        logging.error("No input file specified")
        return 1
    
    if not Path(args.input).exists():
        logging.error(f"Input file not found: {args.input}")
        return 1
    
    # Initialize engine
    engine = PatchEngine(verbose=args.verbose)
    
    # Load image
    if not engine.load(args.input):
        return 1
    
    # Preflight checks
    if not args.dry:
        if not engine.preflight(force=args.force):
            return 1
    
    # Logo operations
    if args.logo_list:
        engine.logo_mgr.scan()
        engine.logo_mgr.list_logos()
        return 0
    
    if args.logo_extract:
        engine.logo_mgr.scan()
        if engine.logo_mgr.logos:
            engine.logo_mgr.extract(0, args.logo_extract)
            return 0
        else:
            logging.error("No logos found")
            return 1
    
    # Build configuration
    config = BIOSConfig()
    
    if args.preset:
        try:
            config = get_preset(args.preset)
            logging.info(f"Using preset: {args.preset}")
        except ValueError as e:
            logging.error(str(e))
            return 1
    
    # Apply individual overrides
    if args.pl1 is not None:
        config.pl1 = args.pl1
    if args.pl2 is not None:
        config.pl2 = args.pl2
    if args.pl3 is not None:
        config.pl3 = args.pl3
    if args.pl4 is not None:
        config.pl4 = args.pl4
    if args.tau is not None:
        config.tau = args.tau
    
    if args.vc is not None:
        config.vcore_offset = args.vc
    if args.rg is not None:
        config.ring_offset = args.rg
    if args.sa is not None:
        config.sa_offset = args.sa
    if args.io is not None:
        config.io_offset = args.io
    
    if args.above_4g is not None:
        config.above_4g = 1 if args.above_4g else 0
    if args.rebar is not None:
        config.resizable_bar = 1 if args.rebar else 0
    
    if args.me_disable:
        config.me_disable = 1
    
    # Apply configuration
    if engine.parser.setup_offset:
        engine.apply_config(config)
    else:
        logging.warning("Setup data not found - skipping Setup patches")
    
    # Logo replacement
    if args.logo:
        engine.logo_mgr.scan()
        if engine.logo_mgr.logos:
            engine.logo_mgr.replace(engine.data, 0, args.logo)
        else:
            logging.warning("No logos found to replace")
    
    if args.logo_color:
        color_name = args.logo_color.lower()
        if color_name not in COLORS:
            logging.error(f"Unknown color: {color_name}. Available: {', '.join(COLORS.keys())}")
            return 1
        
        color = COLORS[color_name]
        logo_data = engine.logo_mgr.generate_solid_color(1024, 768, color)
        
        # Save temp file and replace
        temp_logo = '/tmp/g5cia_logo.bmp'
        Path(temp_logo).write_bytes(logo_data)
        
        engine.logo_mgr.scan()
        if engine.logo_mgr.logos:
            engine.logo_mgr.replace(engine.data, 0, temp_logo)
        else:
            logging.warning("No logos found to replace")
    
    if args.logo_gradient:
        grad_name = args.logo_gradient.lower()
        if grad_name not in GRADIENTS:
            logging.error(f"Unknown gradient: {grad_name}. Available: {', '.join(GRADIENTS.keys())}")
            return 1
        
        c1, c2 = GRADIENTS[grad_name]
        logo_data = engine.logo_mgr.generate_gradient(1024, 768, c1, c2)
        
        temp_logo = '/tmp/g5cia_logo.bmp'
        Path(temp_logo).write_bytes(logo_data)
        
        engine.logo_mgr.scan()
        if engine.logo_mgr.logos:
            engine.logo_mgr.replace(engine.data, 0, temp_logo)
        else:
            logging.warning("No logos found to replace")
    
    # ReBAR injection
    if args.rebar_inject:
        if not engine.inject_rebar_driver(args.rebar_driver, force=args.force):
            logging.error("ReBAR injection failed")
            return 1
    
    # Microcode injection
    if args.uc_path:
        logging.warning("Microcode injection not fully implemented in this version")
    
    # Save output
    if args.dry:
        logging.info("DRY RUN: No output file written")
        engine.print_summary()
        return 0
    
    output_path = args.output or args.input.replace('.bin', '_MOD.bin')
    
    if not engine.save(output_path):
        return 1
    
    # Print summary
    if args.rpt:
        engine.print_summary()
    
    logging.info(f"\n✓ Success! Modded BIOS saved to: {output_path}\n")
    
    # Flash if requested
    if args.flash:
        from .flash.flasher import Flasher
        
        logging.info("Initiating flash operation...")
        
        # Create flasher
        flash_tool = getattr(args, 'flash_tool', None)
        flasher = Flasher(tool_name=flash_tool)
        
        if not flasher.is_available():
            logging.error("No flash tool available - use --flash-detect to check")
            return 1
        
        # Create backup if requested
        if args.flash_backup:
            logging.info(f"Creating backup to {args.flash_backup}...")
            if not flasher.backup(Path(args.flash_backup)):
                logging.error("Backup failed - aborting flash")
                return 1
        
        # Flash the modded BIOS
        modded_data = Path(output_path).read_bytes()
        
        if flasher.flash(modded_data, verify=True):
            logging.info("✓ Flash operation completed successfully!")
            logging.info("⚠️  Reboot your system to apply changes")
            return 0
        else:
            logging.error("✗ Flash operation failed")
            return 1
    
    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='g5cia',
        description='G5 CIA Ultimate - Dell G5 5090 BIOS/UEFI Modding Toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # NVRAM operations (instant, no flash)
  python -m g5cia --nv-report
  python -m g5cia --nv-backup setup.backup
  python -m g5cia --nv-restore setup.backup
  
  # BIOS patching
  python -m g5cia bios.bin --preset gaming -o MOD.bin
  python -m g5cia bios.bin --vc -50 --rg -30 --pl1 85 --pl2 105
  python -m g5cia bios.bin --preset max --logo-color stealth
  python -m g5cia bios.bin --logo-gradient cyber --rebar-inject
  
  # Logo operations
  python -m g5cia bios.bin --logo-list
  python -m g5cia bios.bin --logo-extract boot.bmp
  python -m g5cia bios.bin --logo custom_logo.bmp -o MOD.bin
  
  # Dry run (no output)
  python -m g5cia bios.bin --preset max --dry --rpt
        """
    )
    
    parser.add_argument('input', nargs='?', help='Input BIOS image file')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    # NVRAM operations
    nvram_group = parser.add_argument_group('NVRAM operations (instant, no flash)')
    nvram_group.add_argument('--nv-report', action='store_true', help='Show NVRAM access report')
    nvram_group.add_argument('--nv-backup', dest='backup_file', metavar='FILE', help='Backup Setup to file')
    nvram_group.add_argument('--nv-restore', dest='restore_file', metavar='FILE', help='Restore Setup from file')
    nvram_group.add_argument('--nv-unlock', action='store_true', help='Unlock via NVRAM (no flash)')
    nvram_group.add_argument('--nv-apply', dest='nv_preset', metavar='PRESET', help='Apply preset via NVRAM')
    
    # Preset and configuration
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument('--preset', choices=list_presets(), help='Configuration preset')
    config_group.add_argument('--pl1', type=int, metavar='W', help='PL1 power limit (watts)')
    config_group.add_argument('--pl2', type=int, metavar='W', help='PL2 power limit (watts)')
    config_group.add_argument('--pl3', type=int, metavar='W', help='PL3 power limit (watts)')
    config_group.add_argument('--pl4', type=int, metavar='W', help='PL4 power limit (watts)')
    config_group.add_argument('--tau', type=int, metavar='SEC', help='Turbo time window (seconds)')
    config_group.add_argument('--vc', type=int, metavar='MV', help='Vcore offset (mV, negative=undervolt)')
    config_group.add_argument('--rg', type=int, metavar='MV', help='Ring offset (mV)')
    config_group.add_argument('--sa', type=int, metavar='MV', help='SA offset (mV)')
    config_group.add_argument('--io', type=int, metavar='MV', help='IO offset (mV)')
    config_group.add_argument('--above-4g', action='store_true', help='Enable Above 4G Decoding')
    config_group.add_argument('--rebar', action='store_true', help='Enable Resizable BAR')
    config_group.add_argument('--me-disable', action='store_true', help='Disable Management Engine (HAP)')
    
    # Logo operations
    logo_group = parser.add_argument_group('Logo operations')
    logo_group.add_argument('--logo', metavar='FILE', help='Replace logo with image file')
    logo_group.add_argument('--logo-color', metavar='COLOR', help=f'Generate solid color logo ({", ".join(COLORS.keys())})')
    logo_group.add_argument('--logo-gradient', metavar='GRAD', help=f'Generate gradient logo ({", ".join(GRADIENTS.keys())})')
    logo_group.add_argument('--logo-list', action='store_true', help='List logos in firmware')
    logo_group.add_argument('--logo-extract', metavar='FILE', help='Extract first logo to file')
    
    # Advanced
    adv_group = parser.add_argument_group('Advanced')
    adv_group.add_argument('--rebar-inject', action='store_true', help='Inject ReBAR driver')
    adv_group.add_argument('--rebar-driver', metavar='FILE', help='Local ReBAR driver file')
    adv_group.add_argument('--uc-path', metavar='FILE', help='Microcode update file')
    adv_group.add_argument('--uc-cpuid', metavar='HEX', help='Expected CPUID for microcode')
    
    # Flash operations
    flash_group = parser.add_argument_group('Flash operations')
    flash_group.add_argument('--flash-detect', action='store_true', help='Detect available flash tools')
    flash_group.add_argument('--flash', action='store_true', help='Flash modified BIOS directly')
    flash_group.add_argument('--flash-tool', metavar='TOOL', choices=['fpt', 'ch341a', 'afu'], help='Force specific flash tool')
    flash_group.add_argument('--flash-backup', metavar='FILE', help='Create BIOS backup before flashing')
    
    # Modes
    mode_group = parser.add_argument_group('Modes')
    mode_group.add_argument('--dry', action='store_true', help='Dry run (no output file)')
    mode_group.add_argument('--force', action='store_true', help='Force operation (bypass safety checks)')
    mode_group.add_argument('--rpt', action='store_true', help='Print detailed report')
    mode_group.add_argument('--gui', action='store_true', help='Launch graphical interface')
    
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Handle GUI mode
    if args.gui:
        from .gui.app import G5CIAGUI
        app = G5CIAGUI()
        app.run()
        return 0
    
    # Handle flash detection first
    if args.flash_detect:
        from .flash.detector import FlashDetector
        detector = FlashDetector()
        detector.print_report()
        return 0
    
    # Handle NVRAM operations
    if args.nv_report:
        return cmd_nvram_report(args)
    
    if args.backup_file:
        return cmd_nvram_backup(args)
    
    if args.restore_file:
        return cmd_nvram_restore(args)
    
    if args.nv_unlock:
        return cmd_nvram_unlock(args)
    
    if args.nv_preset:
        return cmd_nvram_apply(args)
    
    # BIOS patching requires input file
    return cmd_patch_bios(args)


if __name__ == '__main__':
    sys.exit(main())
