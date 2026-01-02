# G5 CIA Ultimate v2.0 - Dell BIOS Modding Toolkit

Production-grade, modular BIOS/UEFI patching toolkit for Dell desktop systems with advanced features and multi-platform support.

## ⚠️ WARNING

**This tool modifies firmware at a low level. Improper use can brick your system!**

- Always create backups before flashing
- Understand what each option does
- Boot Guard enforcement = instant brick
- Test with `--dry` mode first
- Keep a USB BIOS recovery tool ready

## Features

### 🔧 Core Capabilities v2.0

- **Dynamic IFR Parsing** - Automatically discover BIOS offsets (no static offset dependency)
- **NVRAM Runtime Control** - Modify settings without reflashing (Windows/Linux)
- **Direct Flash Integration** - Flash BIOS directly with FPT, CH341A, or AFU
- **Multi-Platform Support** - Dell G5 5090/5000, XPS 8940, Alienware Aurora R10
- **Firmware Parsing** - Parse FV/FFS structure, decompress LZMA sections
- **Security Analysis** - Detect Boot Guard, ME, PFAT with hard-fail on dangerous conditions
- **Smart Patching** - Power limits, voltage offsets, unlock bits, ME disable (HAP)
- **ReBAR Injection** - Automated Resizable BAR driver injection
- **Logo Management** - Extract/replace/generate boot logos
- **Option ROM Management** - Extract, update, and replace VBIOS/LAN/RAID ROMs
- **ACPI Support** - Extract and patch DSDT/SSDT tables
- **Preset Configurations** - Stock, balanced, gaming, max, silent, undervolt, bare
- **Cross-Platform GUI** - Modern tkinter-based graphical interface

### 🛡️ Safety Features v2.0

- Boot Guard detection with hard-fail on verified boot
- PFAT/FD lock detection
- Platform-specific VRM limit validation
- Dynamic offset discovery with static fallback
- Overlap detection for patches
- Atomic save with verification
- Read-back verify for critical writes and flash operations
- Detailed logging with patch audit trail
- Auto-backup creation before NVRAM/flash operations

## Installation

```bash
git clone https://github.com/BiosLord/Awesome-Sauce.git
cd Awesome-Sauce
# No dependencies required for core functionality!
```

## Quick Start

### GUI Mode (New in v2.0!)

```bash
# Launch graphical interface
python -m g5cia --gui
```

The GUI provides:
- Easy file selection with browse dialogs
- Visual preset selection and configuration
- Real-time log output
- One-click NVRAM operations
- Integrated flash tool detection
- Dry run testing

### NVRAM Operations (Instant, No Flash)

```bash
# Check NVRAM access
python -m g5cia --nv-report

# Backup current Setup
python -m g5cia --nv-backup setup_backup.bin

# Restore Setup
python -m g5cia --nv-restore setup_backup.bin

# Unlock CFG/OC locks via NVRAM (NEW v2.0!)
python -m g5cia --nv-unlock

# Dry run unlock (test without changes)
python -m g5cia --nv-unlock --dry
```

### BIOS Patching

```bash
# Apply gaming preset with custom logo
python -m g5cia bios.bin --preset gaming --logo-color stealth -o MOD.bin

# Aggressive performance with undervolt
python -m g5cia bios.bin --preset max --vc -50 --rg -30 -o MOD.bin

# Conservative undervolt only
python -m g5cia bios.bin --vc -75 --rg -60 --sa -50 --io -50 -o MOD.bin

# Enable ReBAR
python -m g5cia bios.bin --above-4g --rebar --rebar-inject -o MOD.bin

# Custom power limits
python -m g5cia bios.bin --pl1 85 --pl2 105 --tau 40 -o MOD.bin

# Cyber aesthetic with gradient logo
python -m g5cia bios.bin --logo-gradient cyber --preset gaming -o MOD.bin

# Disable Management Engine
python -m g5cia bios.bin --me-disable -o MOD.bin
```

### Logo Operations

```bash
# List logos in firmware
python -m g5cia bios.bin --logo-list

# Extract logo
python -m g5cia bios.bin --logo-extract boot_logo.bmp

# Replace with custom image
python -m g5cia bios.bin --logo custom.bmp -o MOD.bin

# Generate solid color boot screen
python -m g5cia bios.bin --logo-color black -o MOD.bin

# Generate gradient boot screen
python -m g5cia bios.bin --logo-gradient fire -o MOD.bin
```

### Flash Operations (New in v2.0!)

```bash
# Detect available flash tools
python -m g5cia --flash-detect

# Patch and flash in one step (with backup)
python -m g5cia bios.bin --preset gaming -o MOD.bin --flash --flash-backup backup.bin

# Flash with specific tool
python -m g5cia bios.bin --preset max -o MOD.bin --flash --flash-tool fpt
```

Supported flash tools:
- **Intel FPT** (Flash Programming Tool) - In-system flashing
- **AMI AFU** (BIOS Flash Utility) - Motherboard manufacturer tool
- **CH341A** - External USB SPI programmer (via flashrom)

### Testing & Reports

```bash
# Dry run (no output, show what would be patched)
python -m g5cia bios.bin --preset max --dry --rpt

# Verbose logging
python -m g5cia bios.bin --preset gaming -v --rpt -o MOD.bin

# Force mode (bypass safety checks - DANGEROUS!)
python -m g5cia bios.bin --preset max --force -o MOD.bin
```

## Supported Platforms (New in v2.0!)

### Dell G5 5090
- **Chipset:** Intel B365
- **CPUs:** 9th Gen Intel (i3-9100 to i9-9900)
- **VRM Limits:** PL1 95W, PL2 115W
- **Status:** ✅ Fully tested and supported

### Dell G5 5000
- **Chipset:** Intel B560/H570
- **CPUs:** 11th Gen Intel (Rocket Lake)
- **VRM Limits:** PL1 105W, PL2 125W
- **Status:** ⚠️ Profile created, testing recommended

### Dell XPS 8940
- **Chipset:** Intel Z490/Z590
- **CPUs:** 10th/11th Gen Intel (K-series)
- **VRM Limits:** PL1 125W, PL2 150W
- **Status:** ⚠️ Profile created, testing recommended

### Alienware Aurora R10
- **Chipset:** AMD X570
- **CPUs:** Ryzen 3000/5000 series
- **VRM Limits:** PL1 140W, PL2 170W
- **Status:** ⚠️ AMD platform, experimental

The tool automatically detects platforms from BIOS signatures and validates VRM limits accordingly.

## Configuration Presets

### `stock`
- All locks enabled
- Factory settings
- Safe baseline

### `balanced`
- Unlocked
- PL1: 65W, PL2: 90W
- -25mV undervolt (Vcore/Ring)
- C-states enabled

### `gaming`
- PL1: 80W, PL2: 100W, PL3: 110W
- -20mV undervolt
- Above 4G + ReBAR enabled
- Optimized fan curve

### `max`
- ⚠️ PL1: 95W, PL2: 115W (VRM limits!)
- -10mV light undervolt
- C-states disabled for minimum latency
- Aggressive fan curve

### `silent`
- PL1: 45W, PL2: 65W
- -40mV deep undervolt
- Quiet fan curve (max 80%)
- Max C-states

### `uv` (Undervolt)
- -75mV Vcore, -60mV Ring
- -50mV SA/IO
- Everything else stock

### `bare`
- Unlocked only
- ME disabled
- Minimal modifications

## Command-Line Options

### Configuration
- `--preset <name>` - Apply preset configuration
- `--pl1/2/3/4 <watts>` - Power limits
- `--tau <sec>` - Turbo time window
- `--vc/rg/sa/io <mV>` - Voltage offsets (negative = undervolt)
- `--above-4g` - Enable Above 4G Decoding
- `--rebar` - Enable Resizable BAR
- `--me-disable` - Disable Management Engine (HAP bit)

### Logo Operations
- `--logo <file>` - Replace with custom logo
- `--logo-color <color>` - Solid color (black, stealth, blue, red, green, white)
- `--logo-gradient <name>` - Gradient (cyber, fire, ocean, matrix)
- `--logo-list` - List detected logos
- `--logo-extract <file>` - Extract logo to file

### Advanced
- `--rebar-inject` - Inject ReBAR driver
- `--rebar-driver <file>` - Use local driver file
- `--uc-path <file>` - Inject microcode update
- `--uc-cpuid <hex>` - Expected CPUID

### Flash Operations (v2.0)
- `--flash-detect` - Detect available flash tools
- `--flash` - Flash modified BIOS directly
- `--flash-tool <tool>` - Force specific tool (fpt, ch341a, afu)
- `--flash-backup <file>` - Create backup before flashing

### Modes
- `--dry` - Dry run (no output)
- `--force` - Bypass safety checks (DANGEROUS!)
- `--rpt` - Print detailed report
- `-v, --verbose` - Verbose logging
- `--gui` - Launch graphical interface (v2.0)

## Dynamic Offset Discovery (New in v2.0!)

The v2.0 release introduces **IFR (Internal Forms Representation) parsing** for dynamic offset discovery:

- **Automatic offset detection** - No more broken static offsets after BIOS updates
- **Human-readable names** - Correlates offsets to setting names from BIOS strings
- **Fallback safety** - Uses static offsets when IFR parsing fails
- **Caching** - Performance optimization for repeated operations
- **Multi-BIOS support** - Works across different BIOS versions

This eliminates the primary weakness of v1.0 where BIOS updates would break static offset maps.

## Dell G5 5090 Offset Map

The toolkit includes a complete offset map for the Dell G5 5090 Setup variable:

### Locks
- CFG Lock (0x43) - MSR 0xE2 lock
- OC Lock (0x44) - Overclocking lock
- Power Limit Locks (0x5E, 0x6B)
- BIOS Interface Lock (0x5F)
- SMM/Flash Locks (0x109, 0x10A)

### Power Limits
- PL1/PL2/PL3/PL4 (0x64-0x6F) - Platform power limits
- Tau (0x6A) - Turbo time window

### Voltages
- Vcore Offset (0x70-0x73) - CPU core voltage
- Ring Offset (0x74-0x77) - Ring/cache voltage
- SA Offset (0x78-0x7B) - System Agent
- IO Offset (0x7C-0x7F) - IO voltage

### Turbo
- Turbo Mode (0xA0)
- Per-core ratios (0xA2-0xA7) - 1c to 6c
- Ring ratios (0xA8-0xA9)
- HWP/EPP (0xAA-0xAB)

### Memory
- XMP Profile (0xB0)
- Frequency (0xB1)
- Primary timings (tCL, tRCD, tRP, tRAS, etc.)
- Advanced timings (RTT, ODT, drive strength)

### PCIe
- Above 4G Decoding (0xD0)
- Resizable BAR (0xD1)
- ASPM, L1 Substates (0xD3-0xD4)

### Features
- iGPU, VT-d, VT-x (0x100-0x102)
- TPM, PTT (0x104-0x105)
- ME Enable, HAP (0x106-0x107)

## Architecture v2.0

```
g5cia/
├── __init__.py           # Package metadata
├── __main__.py           # CLI entry point
├── firmware/             # NEW: Firmware parsing modules
│   ├── __init__.py
│   └── ifr.py           # IFR parser for dynamic offsets
├── runtime/              # NEW: Runtime NVRAM operations
│   ├── __init__.py
│   └── nvram_tool.py    # NVRAM unlock tool
├── flash/                # NEW: Flash tool integration
│   ├── __init__.py
│   ├── fpt.py           # Intel FPT wrapper
│   ├── ch341a.py        # CH341A USB programmer
│   ├── afu.py           # AMI AFU wrapper
│   ├── flasher.py       # Unified flash interface
│   └── detector.py      # Auto-detection
├── platforms/            # NEW: Multi-platform support
│   ├── __init__.py
│   ├── hal.py           # Hardware abstraction layer
│   ├── dell_g5_5090.py  # Platform profiles
│   ├── dell_g5_5000.py
│   ├── dell_xps_8940.py
│   └── alienware.py
├── patching/             # NEW: Advanced patching
│   ├── __init__.py
│   ├── optionrom.py     # Option ROM management
│   └── acpi.py          # ACPI table patching
├── gui/                  # NEW: Graphical interface
│   ├── __init__.py
│   ├── app.py           # Main GUI application
│   └── themes.py        # Theme support
├── nvram.py              # Cross-platform NVRAM access
├── image.py              # Firmware volume/file parsing
├── security.py           # Boot Guard, ME, PFAT detection
├── patcher.py            # Byte patching with validation
├── rebar.py              # ReBAR driver injection
├── logo.py               # Logo extraction/generation
├── config.py             # Dataclass configs & presets
├── engine.py             # Main orchestration
├── offsets.py            # Dell G5 5090 offset map (static fallback)
├── utils.py              # Compression, checksums, encoding
└── hw.py                 # Hardware detection
```
├── nvram.py             # Cross-platform NVRAM access
├── image.py             # Firmware volume/file parsing
├── security.py          # Boot Guard, ME, PFAT detection
├── patcher.py           # Byte patching with validation
├── rebar.py             # ReBAR driver injection
├── logo.py              # Logo extraction/generation
├── config.py            # Dataclass configs & presets
├── engine.py            # Main orchestration
├── offsets.py           # Dell G5 5090 offset map
├── utils.py              # Compression, checksums, encoding
└── hw.py                 # Hardware detection
```

## Safety Workflow

1. **Load** - Parse firmware structure
2. **IFR Parse** - Dynamic offset discovery with static fallback (NEW v2.0)
3. **Platform Detect** - Identify system and VRM limits (NEW v2.0)
4. **Preflight** - Detect security features
   - Boot Guard Verified → HARD FAIL
   - PFAT → HARD FAIL
   - Boot Guard Measured → Warning
   - FD Lock → Warning
   - VRM Limit Validation (NEW v2.0)
5. **Patch** - Apply configuration with overlap detection
6. **Verify** - Recalculate checksums, validate structure
7. **Save** - Atomic write with parse verification
8. **Flash** (Optional) - Direct flash with verification (NEW v2.0)

## Flashing v2.0

After creating a modded BIOS, you have multiple options:

### Method 1: Integrated Flash (NEW - Easiest!)
```bash
# Auto-detect and flash
python -m g5cia bios.bin --preset gaming -o MOD.bin --flash --flash-backup backup.bin

# Use GUI for guided flashing
python -m g5cia --gui
```

### Method 2: Intel FPT (In-System)
1. Rename `MOD.bin` to match Dell naming (e.g., `G5_5090_1.2.3.exe`)
```bash
fptw64 -bios -f MOD.bin
```

### Method 3: AMI AFU (Motherboard-Specific)
```bash
afuwin64 MOD.bin /P /N
```

### Method 4: CH341A Programmer (External - Universal)
1. Get CH341A USB SPI programmer
2. Identify BIOS chip (usually 128Mbit Winbond)
3. Use flashrom: `flashrom -p ch341a_spi -w MOD.bin`
4. **Works even with Boot Guard** (before power-on)

### Method 5: NVRAM Only (No Flash)
```bash
python -m g5cia --nv-unlock
```
Changes settings only via NVRAM - no firmware modification. Reset by CMOS clear.

## Recovery

### If System Won't POST

1. **CMOS Clear**
   ```
   - Power off
   - Remove power cable
   - Press CMOS clear button or jumper (consult manual)
   - Wait 30 seconds
   - Restore power
   ```

2. **Dell Ctrl+Esc Recovery**
   ```
   - Power on
   - Immediately press Ctrl+Esc repeatedly
   - Insert USB with BIOS.bin
   - Dell recovery will flash automatically
   ```

3. **SPI Programmer Recovery**
   ```
   - Open case
   - Locate BIOS chip
   - Use CH341A to write backup.bin
   - Reassemble
   ```

## VRM Limits (Dell G5 5090)

**Do not exceed these without VRM cooling mods:**
- **PL1: 95W** (sustained)
- **PL2: 115W** (burst)
- Above these values → VRM overheating → throttling or damage

The `max` preset is at the limit. Monitor VRM temps with HWiNFO64.

## Boot Guard Info

**Boot Guard Verified Boot = INSTANT BRICK if modified**

The toolkit will:
- Detect KEYM/BTGP/ACM signatures
- Parse policy bits
- Hard-fail if verified boot enabled
- Only proceed with `--force` (NOT RECOMMENDED)

If you have Boot Guard verified, your only option is external programmer **before** power-on.

## Contributing

This is a production-grade tool. Contributions welcome:
- Add support for other Dell/Alienware models
- Test and refine platform profiles (G5 5000, XPS 8940, Aurora R10)
- Enhance IFR parser for better compatibility
- Add more flash tool integrations
- Test on different BIOS versions
- Improve GUI with additional features
- Add Option ROM and ACPI use cases

## What's New in v2.0

### Major Features
✅ **Dynamic IFR Parsing** - No more broken offsets after BIOS updates
✅ **NVRAM Unlock** - Instant unlock via `--nv-unlock` without reflashing
✅ **Flash Integration** - Direct flashing with FPT, CH341A, and AFU
✅ **Multi-Platform** - Support for 4 Dell/Alienware systems
✅ **GUI** - Cross-platform graphical interface with tkinter
✅ **Option ROM** - Extract and update VBIOS/LAN/RAID ROMs
✅ **ACPI Support** - Extract and patch DSDT/SSDT tables

### Breaking Changes from v1.0
- Offset discovery is now dynamic by default (static offsets are fallback)
- `--nv-unlock` is now functional (was documented but not implemented in v1.0)
- New `--flash` and `--flash-detect` arguments
- New `--gui` argument for graphical mode

## Credits

- UEFI firmware structure knowledge from TianoCore/EDK2
- ReBAR driver from xCuri0's ReBarUEFI project
- Inspiration from UEFI-Editor, UEFITool, and mei_cleaner

## License

See LICENSE file.

## Disclaimer

**USE AT YOUR OWN RISK**

This tool can brick your system. The authors are not responsible for:
- Bricked motherboards
- Data loss
- Hardware damage
- Warranty voidance
- Any other consequences

Always:
- ✅ Test with `--dry` first
- ✅ Backup original BIOS
- ✅ Have recovery method ready
- ✅ Understand what you're doing
- ❌ Flash with Boot Guard verified
- ❌ Exceed VRM limits without cooling
- ❌ Use on unsupported hardware

## Support

For Dell G5 5090 specific help:
- Check offset map in `g5cia/offsets.py`
- Start with conservative presets (balanced, silent)
- Monitor temps and stability after changes
- Join r/Dell or r/overclocking for community support

---

**G5 CIA Ultimate** - Because your Dell deserves better than locked settings.