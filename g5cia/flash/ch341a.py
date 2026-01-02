"""CH341A USB SPI programmer integration."""

import logging
import subprocess
import shutil
import sys
import tempfile
from typing import Optional
from pathlib import Path

log = logging.getLogger(__name__)


class CH341AFlasher:
    """CH341A USB programmer wrapper."""
    
    def __init__(self):
        self.tool_path: Optional[Path] = None
        self.detected = False
        self.tool_type = None  # 'flashrom', 'ch341prog', or None
        
    def detect(self) -> bool:
        """Check if CH341A programmer and tools are available.
        
        Returns:
            True if CH341A tool is detected
        """
        # Try flashrom first (cross-platform, more common)
        flashrom_path = shutil.which('flashrom')
        if flashrom_path:
            # Check if CH341A is actually connected
            try:
                result = subprocess.run(
                    ['flashrom', '-p', 'ch341a_spi'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # flashrom will error if device not found
                if 'CH341' in result.stdout or 'CH341' in result.stderr:
                    self.tool_path = Path(flashrom_path)
                    self.tool_type = 'flashrom'
                    self.detected = True
                    log.info("Found CH341A via flashrom")
                    return True
            except:
                pass
        
        # Try ch341prog (Linux-specific)
        if sys.platform.startswith('linux'):
            ch341prog_path = shutil.which('ch341prog')
            if ch341prog_path:
                self.tool_path = Path(ch341prog_path)
                self.tool_type = 'ch341prog'
                self.detected = True
                log.info("Found CH341A via ch341prog")
                return True
        
        # Check for USB device (Linux)
        if sys.platform.startswith('linux'):
            try:
                result = subprocess.run(
                    ['lsusb'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # CH341A USB ID: 1a86:5512
                if '1a86:5512' in result.stdout:
                    log.info("CH341A USB device detected but no tool found")
                    log.warning("Install 'flashrom' or 'ch341prog' to use CH341A")
                    return False
            except:
                pass
        
        log.debug("CH341A programmer not detected")
        return False
    
    def read_chip(self, output_path: Path, chip_name: Optional[str] = None) -> bool:
        """Read SPI chip using CH341A.
        
        Args:
            output_path: Where to save the chip dump
            chip_name: Optional chip model (auto-detect if None)
            
        Returns:
            True if successful
        """
        if not self.detected:
            log.error("CH341A not detected - run detect() first")
            return False
        
        try:
            if self.tool_type == 'flashrom':
                cmd = ['flashrom', '-p', 'ch341a_spi', '-r', str(output_path)]
                
                if chip_name:
                    cmd.extend(['-c', chip_name])
                
                log.info(f"Reading chip with flashrom: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0 and output_path.exists():
                    log.info(f"[OK] Chip read successful: {output_path} ({output_path.stat().st_size} bytes)")
                    return True
                else:
                    log.error(f"Flashrom read failed: {result.stderr}")
                    return False
            
            elif self.tool_type == 'ch341prog':
                cmd = [str(self.tool_path), '-r', str(output_path)]
                
                log.info(f"Reading chip with ch341prog: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0 and output_path.exists():
                    log.info(f"[OK] Chip read successful: {output_path}")
                    return True
                else:
                    log.error(f"ch341prog read failed: {result.stderr}")
                    return False
            
            else:
                log.error("Unknown tool type")
                return False
        
        except subprocess.TimeoutExpired:
            log.error("CH341A read timeout (>5 minutes)")
            return False
        except Exception as e:
            log.error(f"CH341A read error: {e}")
            return False
    
    def write_chip(self, data: bytes, chip_name: Optional[str] = None, 
                   verify: bool = True) -> bool:
        """Write SPI chip using CH341A.
        
        Args:
            data: Data to write
            chip_name: Optional chip model
            verify: Verify after write
            
        Returns:
            True if successful
        """
        if not self.detected:
            log.error("CH341A not detected - run detect() first")
            return False
        
        try:
            # Write data to temporary file
            temp_path = Path(tempfile.gettempdir()) / 'g5cia_ch341a_temp.bin'
            temp_path.write_bytes(data)
            
            if self.tool_type == 'flashrom':
                cmd = ['flashrom', '-p', 'ch341a_spi', '-w', str(temp_path)]
                
                if chip_name:
                    cmd.extend(['-c', chip_name])
                
                if verify:
                    cmd.append('-v')
                
                log.info(f"Writing chip with flashrom: {' '.join(cmd)}")
                log.warning("[WARN] This will overwrite your BIOS chip - ensure you have a backup!")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout for write+verify
                )
                
                # Cleanup
                if temp_path.exists():
                    temp_path.unlink()
                
                if result.returncode == 0:
                    log.info("[OK] Chip write successful")
                    return True
                else:
                    log.error(f"Flashrom write failed: {result.stderr}")
                    return False
            
            elif self.tool_type == 'ch341prog':
                cmd = [str(self.tool_path), '-w', str(temp_path)]
                
                log.info(f"Writing chip with ch341prog: {' '.join(cmd)}")
                log.warning("[WARN] This will overwrite your BIOS chip!")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                # Cleanup
                if temp_path.exists():
                    temp_path.unlink()
                
                if result.returncode == 0:
                    log.info("[OK] Chip write successful")
                    
                    # Manual verify if requested
                    if verify:
                        return self._verify_write(data)
                    
                    return True
                else:
                    log.error(f"ch341prog write failed: {result.stderr}")
                    return False
            
            else:
                return False
        
        except subprocess.TimeoutExpired:
            log.error("CH341A write timeout (>10 minutes)")
            return False
        except Exception as e:
            log.error(f"CH341A write error: {e}")
            return False
    
    def erase_chip(self) -> bool:
        """Erase the entire chip.
        
        Returns:
            True if successful
        """
        if not self.detected:
            log.error("CH341A not detected")
            return False
        
        try:
            if self.tool_type == 'flashrom':
                cmd = ['flashrom', '-p', 'ch341a_spi', '-E']
                
                log.info("Erasing chip with flashrom")
                log.warning("[WARN] This will erase your entire BIOS chip!")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    log.info("[OK] Chip erased")
                    return True
                else:
                    log.error(f"Erase failed: {result.stderr}")
                    return False
            
            elif self.tool_type == 'ch341prog':
                cmd = [str(self.tool_path), '-e']
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                return result.returncode == 0
            
            return False
        
        except Exception as e:
            log.error(f"Erase error: {e}")
            return False
    
    def _verify_write(self, original_data: bytes) -> bool:
        """Verify write by reading back.
        
        Args:
            original_data: Original data that was written
            
        Returns:
            True if verification successful
        """
        try:
            verify_path = Path(tempfile.gettempdir()) / 'g5cia_ch341a_verify.bin'
            
            if self.read_chip(verify_path):
                verify_data = verify_path.read_bytes()
                
                # Cleanup
                verify_path.unlink()
                
                if verify_data == original_data:
                    log.info("[OK] Write verification successful")
                    return True
                else:
                    log.error("[FAIL] Write verification failed - data mismatch")
                    return False
            else:
                log.error("[FAIL] Verification read failed")
                return False
        
        except Exception as e:
            log.error(f"Verification error: {e}")
            return False
    
    def get_info(self) -> Optional[dict]:
        """Get CH341A tool info.
        
        Returns:
            Dictionary with tool info or None
        """
        if not self.detected:
            return None
        
        try:
            info = {
                'tool_type': self.tool_type,
                'tool_path': str(self.tool_path) if self.tool_path else None
            }
            
            if self.tool_type == 'flashrom':
                result = subprocess.run(
                    ['flashrom', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                info['version'] = result.stdout.strip()
            
            return info
        
        except Exception as e:
            log.error(f"Error getting CH341A info: {e}")
            return None
