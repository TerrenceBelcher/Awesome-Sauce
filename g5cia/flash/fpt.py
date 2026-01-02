"""Intel Flash Programming Tool (FPT) integration."""

import logging
import subprocess
import shutil
import tempfile
from typing import Optional
from pathlib import Path

log = logging.getLogger(__name__)


class FPTFlasher:
    """Intel FPT flash tool wrapper."""
    
    def __init__(self):
        self.fpt_path: Optional[Path] = None
        self.detected = False
        
    def detect(self) -> bool:
        """Check if FPT is available.
        
        Returns:
            True if FPT tool is detected
        """
        # Common FPT executable names
        fpt_names = ['fptw64.exe', 'fpt.exe', 'fptw.exe', 'fpt64.exe']
        
        # Check in PATH
        for name in fpt_names:
            path = shutil.which(name)
            if path:
                self.fpt_path = Path(path)
                self.detected = True
                log.info(f"Found Intel FPT at: {self.fpt_path}")
                return True
        
        # Check common locations on Windows
        common_paths = [
            Path('C:/Program Files/Intel/FPT'),
            Path('C:/Program Files (x86)/Intel/FPT'),
            Path('C:/Tools/FPT'),
            Path.home() / 'Downloads' / 'FPT',
        ]
        
        for base_path in common_paths:
            if base_path.exists():
                for name in fpt_names:
                    fpt_exe = base_path / name
                    if fpt_exe.exists():
                        self.fpt_path = fpt_exe
                        self.detected = True
                        log.info(f"Found Intel FPT at: {self.fpt_path}")
                        return True
        
        log.debug("Intel FPT not detected")
        return False
    
    def read_bios(self, output_path: Path) -> bool:
        """Read BIOS using FPT.
        
        Args:
            output_path: Where to save the BIOS dump
            
        Returns:
            True if successful
        """
        if not self.detected:
            log.error("FPT not detected - run detect() first")
            return False
        
        try:
            # Command: fptw64 -bios -d output.bin
            cmd = [str(self.fpt_path), '-bios', '-d', str(output_path)]
            
            log.info(f"Reading BIOS with FPT: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                if output_path.exists():
                    log.info(f"[OK] BIOS read successful: {output_path} ({output_path.stat().st_size} bytes)")
                    return True
                else:
                    log.error("FPT reported success but output file not found")
                    return False
            else:
                log.error(f"FPT read failed: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            log.error("FPT read timeout (>5 minutes)")
            return False
        except Exception as e:
            log.error(f"FPT read error: {e}")
            return False
    
    def write_bios(self, data: bytes) -> bool:
        """Write BIOS using FPT.
        
        Args:
            data: BIOS data to write
            
        Returns:
            True if successful
        """
        if not self.detected:
            log.error("FPT not detected - run detect() first")
            return False
        
        try:
            # Write data to temporary file
            temp_path = Path(tempfile.gettempdir()) / 'g5cia_fpt_temp.bin'
            temp_path.write_bytes(data)
            
            # Command: fptw64 -bios -f input.bin
            cmd = [str(self.fpt_path), '-bios', '-f', str(temp_path)]
            
            log.info(f"Writing BIOS with FPT: {' '.join(cmd)}")
            log.warning("[WARN] This will modify your BIOS - ensure you have a backup!")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink()
            
            if result.returncode == 0:
                log.info("[OK] BIOS write successful")
                return True
            else:
                log.error(f"FPT write failed: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            log.error("FPT write timeout (>5 minutes)")
            return False
        except Exception as e:
            log.error(f"FPT write error: {e}")
            return False
    
    def verify(self) -> bool:
        """Verify BIOS write by reading back.
        
        Returns:
            True if verification successful
        """
        if not self.detected:
            return False
        
        try:
            verify_path = Path(tempfile.gettempdir()) / 'g5cia_verify.bin'
            
            if self.read_bios(verify_path):
                log.info("[OK] Verification read successful")
                
                # Cleanup
                if verify_path.exists():
                    verify_path.unlink()
                
                return True
            else:
                return False
        
        except Exception as e:
            log.error(f"Verification error: {e}")
            return False
    
    def get_info(self) -> Optional[dict]:
        """Get FPT version and capabilities.
        
        Returns:
            Dictionary with FPT info or None
        """
        if not self.detected:
            return None
        
        try:
            result = subprocess.run(
                [str(self.fpt_path), '-?'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse version from output
            info = {
                'path': str(self.fpt_path),
                'version': 'Unknown',
                'output': result.stdout
            }
            
            # Try to extract version
            for line in result.stdout.split('\n'):
                if 'version' in line.lower():
                    info['version'] = line.strip()
                    break
            
            return info
        
        except Exception as e:
            log.error(f"Error getting FPT info: {e}")
            return None
