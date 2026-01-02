"""Hardware detection utilities."""

import platform
import subprocess
import logging
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)


class HardwareInfo:
    """Container for hardware information."""
    
    def __init__(self):
        self.cpu_model: Optional[str] = None
        self.cpu_cores: Optional[int] = None
        self.cpu_threads: Optional[int] = None
        self.ram_gb: Optional[int] = None
        self.gpu_model: Optional[str] = None
        self.platform: str = platform.system()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'cpu_model': self.cpu_model,
            'cpu_cores': self.cpu_cores,
            'cpu_threads': self.cpu_threads,
            'ram_gb': self.ram_gb,
            'gpu_model': self.gpu_model,
            'platform': self.platform,
        }


def detect_hardware() -> HardwareInfo:
    """Detect system hardware."""
    hw = HardwareInfo()
    
    try:
        if platform.system() == 'Windows':
            _detect_windows(hw)
        elif platform.system() == 'Linux':
            _detect_linux(hw)
        else:
            log.warning(f"Unsupported platform: {platform.system()}")
    except Exception as e:
        log.error(f"Hardware detection failed: {e}")
    
    return hw


def _detect_windows(hw: HardwareInfo) -> None:
    """Detect hardware on Windows."""
    try:
        # CPU info
        result = subprocess.run(
            ['wmic', 'cpu', 'get', 'name,numberofcores,numberoflogicalprocessors', '/format:list'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if 'Name=' in line:
                    hw.cpu_model = line.split('=', 1)[1].strip()
                elif 'NumberOfCores=' in line:
                    hw.cpu_cores = int(line.split('=', 1)[1].strip())
                elif 'NumberOfLogicalProcessors=' in line:
                    hw.cpu_threads = int(line.split('=', 1)[1].strip())
        
        # RAM
        result = subprocess.run(
            ['wmic', 'computersystem', 'get', 'totalphysicalmemory', '/format:list'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if 'TotalPhysicalMemory=' in line:
                    bytes_ram = int(line.split('=', 1)[1].strip())
                    hw.ram_gb = bytes_ram // (1024**3)
        
        # GPU
        result = subprocess.run(
            ['wmic', 'path', 'win32_videocontroller', 'get', 'name', '/format:list'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if 'Name=' in line:
                    hw.gpu_model = line.split('=', 1)[1].strip()
                    break
    
    except Exception as e:
        log.debug(f"Windows hardware detection error: {e}")


def _detect_linux(hw: HardwareInfo) -> None:
    """Detect hardware on Linux."""
    try:
        # CPU info
        with open('/proc/cpuinfo', 'r') as f:
            cores = 0
            for line in f:
                if line.startswith('model name'):
                    if not hw.cpu_model:
                        hw.cpu_model = line.split(':', 1)[1].strip()
                elif line.startswith('processor'):
                    cores += 1
            hw.cpu_threads = cores
        
        # Try lscpu for core count
        try:
            result = subprocess.run(['lscpu'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if 'Core(s) per socket' in line:
                        hw.cpu_cores = int(line.split(':')[1].strip())
        except:
            pass
        
        # RAM
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal'):
                    kb_ram = int(line.split()[1])
                    hw.ram_gb = kb_ram // (1024**2)
                    break
        
        # GPU - try lspci
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if 'VGA' in line or '3D controller' in line:
                        hw.gpu_model = line.split(':', 1)[1].strip()
                        break
        except:
            pass
    
    except Exception as e:
        log.debug(f"Linux hardware detection error: {e}")


def check_cpu_compat(cpu_model: Optional[str]) -> tuple[bool, str]:
    """Check if CPU is compatible with Dell G5 5090 patches.
    
    Returns:
        (is_compatible, message)
    """
    if not cpu_model:
        return (True, "Could not detect CPU, proceeding with caution")
    
    # Dell G5 5090 typically ships with 9th/10th gen Intel
    compatible_cpus = [
        'i5-9400', 'i5-9600K', 'i7-9700', 'i7-9700K', 'i9-9900', 'i9-9900K',
        'i5-10400', 'i5-10600K', 'i7-10700', 'i7-10700K', 'i9-10900', 'i9-10900K'
    ]
    
    for compat in compatible_cpus:
        if compat in cpu_model:
            return (True, f"Compatible CPU detected: {cpu_model}")
    
    return (False, f"WARNING: Non-standard CPU detected: {cpu_model}. Dell G5 5090 typically uses 9th/10th gen Intel")
