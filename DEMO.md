# G5 CIA Ultimate - Live Demonstration

This document demonstrates the toolkit's capabilities.

## Installation Check

```bash
$ python -m g5cia --version
g5cia 1.0.0
```

## Feature Overview

```bash
$ python -m g5cia --help | head -20
usage: g5cia [-h] [-o OUTPUT] [-v] [--version] [--nv-report] ...

G5 CIA Ultimate - Dell G5 5090 BIOS/UEFI Modding Toolkit

positional arguments:
  input                 Input BIOS image file

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file path
  -v, --verbose         Verbose logging
  --version             show program's version number and exit
...
```

## NVRAM Operations

```bash
$ python -m g5cia --nv-report
======================================================================
NVRAM ACCESS REPORT
======================================================================
Platform: linux
NVRAM Access: ✗ Not available

To enable NVRAM access on Linux:
  1. Run as root (sudo)
  2. Ensure efivarfs is mounted
======================================================================
```

## Configuration Presets

Available presets demonstrate different use cases:

1. **stock** - Factory settings (all locks enabled)
2. **balanced** - 65W/90W, -25mV UV, C-states enabled
3. **perf** - 85W/105W, -15mV UV, reduced C-states
4. **gaming** - 80W/100W/110W, -20mV UV, ReBAR ready
5. **max** - ⚠️ 95W/115W (VRM limits!), minimal UV
6. **silent** - 45W/65W, -40mV deep UV, quiet fans
7. **uv** - -75mV aggressive undervolt only
8. **bare** - Unlocked, ME disabled, minimal changes

## Dry Run Example

```bash
$ python -m g5cia test_bios.bin --preset gaming --dry --rpt

INFO     Loading firmware image: test_bios.bin
INFO     Parsed 1 firmware volumes
INFO     Setup base set to 0x1000
INFO     Using preset: gaming
INFO     Applying preset: gaming
INFO     Set Pl1 to 80W
INFO     Set Pl2 to 100W
INFO     Set Pl3 to 110W
INFO     Set Vc offset to -20mV
INFO     Set Rg offset to -20mV
INFO     ✓ Applied 14 patches
INFO     DRY RUN: No output file written

======================================================================
OPERATION SUMMARY
======================================================================
Input size:       65,536 bytes
Patches applied:  14
Boot Guard:       No
ME region:        Not found
Safe to flash:    ✓ Yes
======================================================================
```

## Logo Generation

Generate custom boot logos:

```bash
# Solid black stealth mode
$ python -m g5cia bios.bin --logo-color stealth -o stealthy.bin

# Cyberpunk gradient
$ python -m g5cia bios.bin --logo-gradient cyber -o cyber.bin

# Available colors: black, stealth, blue, red, green, white
# Available gradients: cyber, fire, ocean, matrix
```

## Safety Features in Action

### Boot Guard Detection
```
WARNING: Boot Guard KEYM found at 0x12345
CRITICAL: Boot Guard Verified Boot is ENABLED
UNSAFE TO FLASH: Boot Guard Verified Boot is enabled
✗ CRITICAL security blocks detected - DO NOT FLASH!
```

### VRM Warnings
```
⚠️  PL1 95W exceeds Dell G5 5090 VRM spec (95W)
⚠️  PL2 115W exceeds Dell G5 5090 VRM spec (115W)
```

## Custom Configuration

Combine individual options:

```bash
# Custom power + undervolt
$ python -m g5cia bios.bin --pl1 85 --pl2 105 --vc -50 --rg -30

# Enable ReBAR with injection
$ python -m g5cia bios.bin --above-4g --rebar --rebar-inject

# Disable ME (HAP bit)
$ python -m g5cia bios.bin --me-disable
```

## Advanced Usage

```bash
# Verbose with full report
$ python -m g5cia bios.bin --preset max -v --rpt -o MOD.bin

# Force mode (bypass safety - DANGEROUS!)
$ python -m g5cia bios.bin --preset max --force -o DANGER.bin
```

## Typical Workflow

1. **Backup original BIOS**
   ```bash
   # Use programmer to read original
   flashrom -p ch341a_spi -r backup.bin
   ```

2. **Test with dry run**
   ```bash
   python -m g5cia backup.bin --preset gaming --dry --rpt
   ```

3. **Create modded BIOS**
   ```bash
   python -m g5cia backup.bin --preset gaming --logo-color stealth -o MOD.bin
   ```

4. **Flash with programmer**
   ```bash
   flashrom -p ch341a_spi -w MOD.bin
   ```

5. **Test and enjoy!** 🚀

## Offset Map Sample

119 Dell G5 5090 offsets mapped:

```
CfgLk    @ 0x0043 (1B): CFG Lock (MSR 0xE2)
OcLk     @ 0x0044 (1B): Overclocking Lock
Pl1En    @ 0x0064 (1B): PL1 Enable
Pl2En    @ 0x0065 (1B): PL2 Enable
VcOL     @ 0x0070 (1B): Vcore Offset Low
VcOH     @ 0x0071 (1B): Vcore Offset High
...
```

## Statistics

- **Total Code:** ~3,000 lines
- **Modules:** 13 Python files
- **Offsets:** 119 mapped
- **Presets:** 8 configurations
- **Dependencies:** 0 for core features
- **Safety Checks:** 6 hard-fail conditions

---

**Remember:** Always test with `--dry` first, keep backups, and understand the risks!
