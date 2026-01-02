"""Unified flash interface with auto-detection."""

import logging
from typing import Optional
from pathlib import Path

from .detector import FlashDetector
from .fpt import FPTFlasher
from .ch341a import CH341AFlasher
from .afu import AFUFlasher

log = logging.getLogger(__name__)


class Flasher:
    """Unified flash interface with auto-detection."""
    
    def __init__(self, tool_name: Optional[str] = None):
        """Initialize flasher.
        
        Args:
            tool_name: Force specific tool ('fpt', 'ch341a', 'afu'), or None for auto
        """
        self.tool_name = tool_name
        self.tool = None
        self.detector = FlashDetector()
        
        if tool_name:
            self._init_specific_tool(tool_name)
        else:
            self._auto_detect()
    
    def _init_specific_tool(self, tool_name: str) -> None:
        """Initialize a specific flash tool.
        
        Args:
            tool_name: Tool name ('fpt', 'ch341a', 'afu')
        """
        tool_name = tool_name.lower()
        
        if tool_name == 'fpt':
            self.tool = FPTFlasher()
            if self.tool.detect():
                self.tool_name = 'fpt'
            else:
                log.error("Intel FPT not detected")
                self.tool = None
        
        elif tool_name == 'ch341a':
            self.tool = CH341AFlasher()
            if self.tool.detect():
                self.tool_name = 'ch341a'
            else:
                log.error("CH341A not detected")
                self.tool = None
        
        elif tool_name == 'afu':
            self.tool = AFUFlasher()
            if self.tool.detect():
                self.tool_name = 'afu'
            else:
                log.error("AMI AFU not detected")
                self.tool = None
        
        else:
            log.error(f"Unknown flash tool: {tool_name}")
    
    def _auto_detect(self) -> None:
        """Auto-detect best available flash tool."""
        recommended = self.detector.get_recommended()
        
        if recommended:
            self.tool_name, self.tool = recommended
            log.info(f"Auto-selected flash tool: {self.tool_name}")
        else:
            log.warning("No flash tools detected")
    
    def auto_detect(self) -> Optional[str]:
        """Auto-detect available flash tools.
        
        Returns:
            Tool name if detected, None otherwise
        """
        self._auto_detect()
        return self.tool_name
    
    def backup(self, path: Path) -> bool:
        """Backup current BIOS to file.
        
        Args:
            path: Output file path
            
        Returns:
            True if successful
        """
        if not self.tool:
            log.error("No flash tool available")
            return False
        
        log.info(f"Creating BIOS backup to: {path}")
        
        if self.tool_name == 'fpt':
            return self.tool.read_bios(path)
        
        elif self.tool_name == 'ch341a':
            return self.tool.read_chip(path)
        
        elif self.tool_name == 'afu':
            return self.tool.read_bios(path)
        
        return False
    
    def flash(self, data: bytes, verify: bool = True) -> bool:
        """Flash BIOS data.
        
        Args:
            data: BIOS data to flash
            verify: Verify after flashing
            
        Returns:
            True if successful
        """
        if not self.tool:
            log.error("No flash tool available")
            return False
        
        log.warning("="*70)
        log.warning("[WARN] BIOS FLASH OPERATION")
        log.warning("="*70)
        log.warning("This will modify your BIOS firmware.")
        log.warning("Ensure you have a working backup before proceeding.")
        log.warning("Power loss during flashing can brick your system!")
        log.warning("="*70)
        
        # Flash based on tool type
        success = False
        
        if self.tool_name == 'fpt':
            success = self.tool.write_bios(data)
            
            if success and verify:
                log.info("Verifying flash...")
                success = self.tool.verify()
        
        elif self.tool_name == 'ch341a':
            success = self.tool.write_chip(data, verify=verify)
        
        elif self.tool_name == 'afu':
            success = self.tool.write_bios(data)
            
            if success and verify:
                log.info("Verifying flash...")
                success = self.tool.verify()
        
        if success:
            log.info("[OK] Flash operation completed successfully")
        else:
            log.error("[FAIL] Flash operation failed")
        
        return success
    
    def restore(self, path: Path) -> bool:
        """Restore BIOS from backup file.
        
        Args:
            path: Backup file path
            
        Returns:
            True if successful
        """
        if not path.exists():
            log.error(f"Backup file not found: {path}")
            return False
        
        log.info(f"Restoring BIOS from: {path}")
        
        data = path.read_bytes()
        return self.flash(data, verify=True)
    
    def get_info(self) -> Optional[dict]:
        """Get flash tool information.
        
        Returns:
            Dictionary with tool info or None
        """
        if not self.tool:
            return None
        
        info = self.tool.get_info() or {}
        info['tool_name'] = self.tool_name
        
        return info
    
    def is_available(self) -> bool:
        """Check if a flash tool is available.
        
        Returns:
            True if a flash tool is ready
        """
        return self.tool is not None
