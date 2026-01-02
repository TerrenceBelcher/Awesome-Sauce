"""Flash tool auto-detection."""

import logging
from typing import Optional, List, Tuple

from .fpt import FPTFlasher
from .ch341a import CH341AFlasher
from .afu import AFUFlasher

log = logging.getLogger(__name__)


class FlashDetector:
    """Auto-detect available flash tools."""
    
    def __init__(self):
        self.available_tools: List[Tuple[str, object]] = []
        
    def detect_all(self) -> List[Tuple[str, object]]:
        """Detect all available flash tools.
        
        Returns:
            List of tuples: (tool_name, tool_instance)
        """
        self.available_tools = []
        
        # Try FPT
        fpt = FPTFlasher()
        if fpt.detect():
            self.available_tools.append(('fpt', fpt))
        
        # Try CH341A
        ch341a = CH341AFlasher()
        if ch341a.detect():
            self.available_tools.append(('ch341a', ch341a))
        
        # Try AFU
        afu = AFUFlasher()
        if afu.detect():
            self.available_tools.append(('afu', afu))
        
        if self.available_tools:
            log.info(f"Detected flash tools: {', '.join([name for name, _ in self.available_tools])}")
        else:
            log.warning("No flash tools detected")
        
        return self.available_tools
    
    def get_recommended(self) -> Optional[Tuple[str, object]]:
        """Get recommended flash tool.
        
        Priority: FPT > AFU > CH341A (FPT safest for in-system)
        
        Returns:
            Tuple of (tool_name, tool_instance) or None
        """
        if not self.available_tools:
            self.detect_all()
        
        if not self.available_tools:
            return None
        
        # Priority order
        priority = ['fpt', 'afu', 'ch341a']
        
        for tool_name in priority:
            for name, tool in self.available_tools:
                if name == tool_name:
                    log.info(f"Recommended flash tool: {tool_name}")
                    return (name, tool)
        
        # Return first available if none match priority
        return self.available_tools[0]
    
    def print_report(self) -> None:
        """Print flash tool detection report."""
        if not self.available_tools:
            self.detect_all()
        
        print("\n" + "="*70)
        print("FLASH TOOL DETECTION REPORT")
        print("="*70)
        
        if not self.available_tools:
            print("[FAIL] No flash tools detected")
            print("\nTo enable flashing:")
            print("  - Intel FPT: Download from Intel ME System Tools")
            print("  - AMI AFU: Download from motherboard manufacturer")
            print("  - CH341A: Install 'flashrom' or 'ch341prog' and connect programmer")
        else:
            print(f"[OK] Detected {len(self.available_tools)} flash tool(s):\n")
            
            for name, tool in self.available_tools:
                print(f"  [{name.upper()}]")
                
                info = tool.get_info()
                if info:
                    if 'version' in info:
                        print(f"    Version: {info['version']}")
                    if 'path' in info:
                        print(f"    Path: {info['path']}")
                    if 'tool_type' in info:
                        print(f"    Tool Type: {info['tool_type']}")
                print()
            
            recommended = self.get_recommended()
            if recommended:
                print(f"Recommended: {recommended[0].upper()}")
        
        print("="*70 + "\n")
