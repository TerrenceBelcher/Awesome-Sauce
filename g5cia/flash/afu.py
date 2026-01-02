"""AMI Aptio Flash Utility (AFU) integration."""

import logging
import subprocess
import shutil
import tempfile
from typing import Optional
from pathlib import Path

log = logging.getLogger(__name__)


class AFUFlasher:
    """AMI AFU flash tool wrapper."""
    
    def __init__(self):
        self.afu_path: Optional[Path] = None
        self.detected = False
        
    def detect(self) -> bool:
        """Check if AFU is available.
        
        Returns:
            True if AFU tool is detected
        """
        # Common AFU executable names
        afu_names = ['afu.exe', 'afuwin.exe', 'afuwin64.exe', 'afudos.exe']
        
        # Check in PATH
        for name in afu_names:
            path = shutil.which(name)
            if path:
                self.afu_path = Path(path)
                self.detected = True
                log.info(f"Found AMI AFU at: {self.afu_path}")
                return True
        
        # Check common locations
        common_paths = [
            Path('C:/Program Files/AMI/AFU'),
            Path('C:/Program Files (x86)/AMI/AFU'),
            Path('C:/Tools/AFU'),
            Path.home() / 'Downloads' / 'AFU',
        ]
        
        for base_path in common_paths:
            if base_path.exists():
                for name in afu_names:
                    afu_exe = base_path / name
                    if afu_exe.exists():
                        self.afu_path = afu_exe
                        self.detected = True
                        log.info(f"Found AMI AFU at: {self.afu_path}")
                        return True
        
        log.debug("AMI AFU not detected")
        return False
    
    def read_bios(self, output_path: Path) -> bool:
        """Read BIOS using AFU.
        
        Args:
            output_path: Where to save the BIOS dump
            
        Returns:
            True if successful
        """
        if not self.detected:
            log.error("AFU not detected - run detect() first")
            return False
        
        try:
            # Command: afuwin64 /O output.bin
            cmd = [str(self.afu_path), '/O', str(output_path)]
            
            log.info(f"Reading BIOS with AFU: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                if output_path.exists():
                    log.info(f"[OK] BIOS read successful: {output_path} ({output_path.stat().st_size} bytes)")
                    return True
                else:
                    log.error("AFU reported success but output file not found")
                    return False
            else:
                log.error(f"AFU read failed: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            log.error("AFU read timeout (>5 minutes)")
            return False
        except Exception as e:
            log.error(f"AFU read error: {e}")
            return False
    
    def write_bios(self, data: bytes, preserve_settings: bool = True) -> bool:
        """Write BIOS using AFU.
        
        Args:
            data: BIOS data to write
            preserve_settings: Preserve NVRAM/settings (/P flag)
            
        Returns:
            True if successful
        """
        if not self.detected:
            log.error("AFU not detected - run detect() first")
            return False
        
        try:
            # Write data to temporary file
            temp_path = Path(tempfile.gettempdir()) / 'g5cia_afu_temp.bin'
            temp_path.write_bytes(data)
            
            # Command: afuwin64 input.bin [/P] [/N] [/B]
            cmd = [str(self.afu_path), str(temp_path)]
            
            if preserve_settings:
                cmd.append('/P')  # Preserve NVRAM
            
            cmd.append('/N')  # No reboot prompt
            
            log.info(f"Writing BIOS with AFU: {' '.join(cmd)}")
            log.warning("[WARN] This will modify your BIOS - ensure you have a backup!")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()
            
            if result.returncode == 0:
                log.info("[OK] BIOS write successful")
                return True
            else:
                log.error(f"AFU write failed: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            log.error("AFU write timeout (>5 minutes)")
            return False
        except Exception as e:
            log.error(f"AFU write error: {e}")
            return False
    
    def verify(self) -> bool:
        """Verify BIOS write by reading back.
        
        Returns:
            True if verification successful
        """
        if not self.detected:
            return False
        
        try:
            verify_path = Path(tempfile.gettempdir()) / 'g5cia_afu_verify.bin'
            
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
        """Get AFU version and capabilities.
        
        Returns:
            Dictionary with AFU info or None
        """
        if not self.detected:
            return None
        
        try:
            result = subprocess.run(
                [str(self.afu_path), '/?'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            info = {
                'path': str(self.afu_path),
                'version': 'Unknown',
                'output': result.stdout
            }
            
            # Try to extract version
            for line in result.stdout.split('\n'):
                if 'version' in line.lower() or 'aptio' in line.lower():
                    info['version'] = line.strip()
                    break
            
            return info
        
        except Exception as e:
            log.error(f"Error getting AFU info: {e}")
            return None
