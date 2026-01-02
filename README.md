# G5 CIA Ultimate - Dell G5 5090 BIOS Modding Toolkit

Production-grade, modular BIOS/UEFI patching toolkit for Dell G5 5090 desktop systems.

## ⚠️ WARNING

**This tool modifies firmware at a low level. Improper use can brick your system!**

- Always create backups before flashing
- Understand what each option does
- Boot Guard enforcement = instant brick
- Test with `--dry` mode first
- Keep a USB BIOS recovery tool ready

## Features

### 🔧 Core Capabilities

- **NVRAM Runtime Control** - Modify settings without reflashing (Windows/Linux)
- **Firmware Parsing** - Parse FV/FFS structure, decompress LZMA sections
- **Security Analysis** - Detect Boot Guard, ME, PFAT with hard-fail on dangerous conditions
- **Smart Patching** - Power limits, voltage offsets, unlock bits, ME disable (HAP)
- **ReBAR Injection** - Automated Resizable BAR driver injection
- **Logo Management** - Extract/replace/generate boot logos
- **Microcode Updates** - Inject updated microcode with validation
- **Preset Configurations** - Stock, balanced, gaming, max, silent, undervolt, bare

### 🛡️ Safety Features

- Boot Guard detection with hard-fail on verified boot
- PFAT/FD lock detection
- VRM limit warnings (95W PL1, 115W PL2 for G5 5090)
- Overlap detection for patches
- Atomic save with verification
- Read-back verify for critical writes
- Detailed logging with patch audit trail

## Installation

```bash
git clone https://github.com/BiosLord/Awesome-Sauce.git
cd Awesome-Sauce
# No dependencies required for core functionality!
```

## Quick Start

### NVRAM Operations (Instant, No Flash)

```bash
# Check NVRAM access
python -m g5cia --nv-report

# Backup current Setup
python -m g5cia --nv-backup setup_backup.bin

# Restore Setup
python -m g5cia --nv-restore setup_backup.bin

# Unlock CFG/OC locks (not yet implemented)
python -m g5cia --nv-unlock
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

### Testing & Reports

```bash
# Dry run (no output, show what would be patched)
python -m g5cia bios.bin --preset max --dry --rpt

# Verbose logging
python -m g5cia bios.bin --preset gaming -v --rpt -o MOD.bin

# Force mode (bypass safety checks - DANGEROUS!)
python -m g5cia bios.bin --preset max --force -o MOD.bin
```

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

### Modes
- `--dry` - Dry run (no output)
- `--force` - Bypass safety checks (DANGEROUS!)
- `--rpt` - Print detailed report
- `-v, --verbose` - Verbose logging

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

## Architecture

```
g5cia/
├── __init__.py          # Package metadata
├── __main__.py          # CLI entry point
├── nvram.py             # Cross-platform NVRAM access
├── image.py             # Firmware volume/file parsing
├── security.py          # Boot Guard, ME, PFAT detection
├── patcher.py           # Byte patching with validation
├── rebar.py             # ReBAR driver injection
├── logo.py              # Logo extraction/generation
├── config.py            # Dataclass configs & presets
├── engine.py            # Main orchestration
├── offsets.py           # Dell G5 5090 offset map
├── utils.py             # Compression, checksums, encoding
└── hw.py                # Hardware detection
```

## Safety Workflow

1. **Load** - Parse firmware structure
2. **Preflight** - Detect security features
   - Boot Guard Verified → HARD FAIL
   - PFAT → HARD FAIL
   - Boot Guard Measured → Warning
   - FD Lock → Warning
3. **Patch** - Apply configuration with overlap detection
4. **Verify** - Recalculate checksums, validate structure
5. **Save** - Atomic write with parse verification

## Flashing

After creating a modded BIOS:

### Method 1: Dell BIOS Update (Safest)
1. Rename `MOD.bin` to match Dell naming (e.g., `G5_5090_1.2.3.exe`)
2. Run Dell BIOS updater
3. **Only works if Boot Guard is NOT enforced**

### Method 2: External Programmer (Universal)
1. Get CH341A or equivalent SPI programmer
2. Identify BIOS chip (usually 128Mbit Winbond)
3. Read current BIOS for backup
4. Write `MOD.bin`
5. **Works even with Boot Guard** (before power-on)

### Method 3: NVRAM (No Flash)
1. `python -m g5cia --nv-apply gaming`
2. Changes settings only, no firmware modification
3. Reset by CMOS clear

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

This is a production tool. Contributions welcome:
- Add support for other Dell models
- Improve IFR parsing for dynamic offsets
- Add more presets
- Test on different G5 5090 BIOS versions

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