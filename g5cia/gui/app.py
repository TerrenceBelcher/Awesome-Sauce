"""Main GUI application for G5 CIA Ultimate."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import logging
import threading
from pathlib import Path
from typing import Optional

from ..config import BIOSConfig, get_preset, list_presets
from ..engine import PatchEngine
from ..nvram import NVRAMAccess
from ..runtime.nvram_tool import NVRAMUnlocker
from ..flash.detector import FlashDetector
from ..flash.flasher import Flasher
from .themes import apply_theme


class G5CIAGUI:
    """Main GUI application for G5 CIA Ultimate."""
    
    def __init__(self):
        """Initialize the GUI."""
        self.root = tk.Tk()
        self.root.title("G5 CIA Ultimate v2.0 - BIOS Modding Toolkit")
        self.root.geometry("900x700")
        
        # Data
        self.input_file: Optional[str] = None
        self.output_file: Optional[str] = None
        self.config = BIOSConfig()
        self.engine: Optional[PatchEngine] = None
        
        # Setup logging redirection
        self._setup_logging()
        
        # Create UI
        self._create_widgets()
        
        # Apply theme
        apply_theme(self.root)
        
    def _setup_logging(self):
        """Setup logging to capture to GUI."""
        self.log_handler = GUILogHandler()
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # File selection
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="Input BIOS:").grid(row=0, column=0, sticky=tk.W)
        self.input_entry = ttk.Entry(file_frame, width=50)
        self.input_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        ttk.Button(file_frame, text="Browse...", command=self._browse_input).grid(row=0, column=2)
        
        ttk.Label(file_frame, text="Output BIOS:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.output_entry = ttk.Entry(file_frame, width=50)
        self.output_entry.grid(row=1, column=1, padx=5, pady=(5, 0), sticky=(tk.W, tk.E))
        ttk.Button(file_frame, text="Browse...", command=self._browse_output).grid(row=1, column=2, pady=(5, 0))
        
        # Notebook for organized options
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Tab 1: Presets & Power
        power_frame = ttk.Frame(notebook, padding="10")
        notebook.add(power_frame, text="Presets & Power")
        
        # Preset selection
        ttk.Label(power_frame, text="Preset:").grid(row=0, column=0, sticky=tk.W)
        self.preset_var = tk.StringVar()
        preset_combo = ttk.Combobox(power_frame, textvariable=self.preset_var, 
                                     values=list_presets(), state='readonly', width=20)
        preset_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        preset_combo.set('balanced')
        ttk.Button(power_frame, text="Apply Preset", command=self._apply_preset).grid(row=0, column=2, padx=5)
        
        # Power limits
        ttk.Label(power_frame, text="PL1 (W):").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.pl1_var = tk.IntVar(value=65)
        ttk.Spinbox(power_frame, from_=15, to=200, textvariable=self.pl1_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=5)
        
        ttk.Label(power_frame, text="PL2 (W):").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.pl2_var = tk.IntVar(value=90)
        ttk.Spinbox(power_frame, from_=15, to=250, textvariable=self.pl2_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=(5, 0), padx=5)
        
        ttk.Label(power_frame, text="Tau (s):").grid(row=3, column=0, sticky=tk.W, pady=(5, 0))
        self.tau_var = tk.IntVar(value=28)
        ttk.Spinbox(power_frame, from_=1, to=128, textvariable=self.tau_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=(5, 0), padx=5)
        
        # Tab 2: Voltage Offsets
        voltage_frame = ttk.Frame(notebook, padding="10")
        notebook.add(voltage_frame, text="Voltage Offsets")
        
        ttk.Label(voltage_frame, text="Vcore Offset (mV):").grid(row=0, column=0, sticky=tk.W)
        self.vcore_var = tk.IntVar(value=-25)
        ttk.Spinbox(voltage_frame, from_=-200, to=200, textvariable=self.vcore_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(voltage_frame, text="Ring Offset (mV):").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.ring_var = tk.IntVar(value=-25)
        ttk.Spinbox(voltage_frame, from_=-200, to=200, textvariable=self.ring_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=(5, 0), padx=5)
        
        ttk.Label(voltage_frame, text="SA Offset (mV):").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.sa_var = tk.IntVar(value=0)
        ttk.Spinbox(voltage_frame, from_=-200, to=200, textvariable=self.sa_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=(5, 0), padx=5)
        
        ttk.Label(voltage_frame, text="IO Offset (mV):").grid(row=3, column=0, sticky=tk.W, pady=(5, 0))
        self.io_var = tk.IntVar(value=0)
        ttk.Spinbox(voltage_frame, from_=-200, to=200, textvariable=self.io_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=(5, 0), padx=5)
        
        # Tab 3: Features
        features_frame = ttk.Frame(notebook, padding="10")
        notebook.add(features_frame, text="Features")
        
        self.cfg_unlock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(features_frame, text="Unlock CFG Lock", variable=self.cfg_unlock_var).grid(row=0, column=0, sticky=tk.W)
        
        self.oc_unlock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(features_frame, text="Unlock OC Lock", variable=self.oc_unlock_var).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        self.above_4g_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(features_frame, text="Enable Above 4G Decoding", variable=self.above_4g_var).grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        
        self.rebar_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(features_frame, text="Enable Resizable BAR", variable=self.rebar_var).grid(row=3, column=0, sticky=tk.W, pady=(5, 0))
        
        self.me_disable_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(features_frame, text="Disable Management Engine", variable=self.me_disable_var).grid(row=4, column=0, sticky=tk.W, pady=(5, 0))
        
        # Tab 4: NVRAM Operations
        nvram_frame = ttk.Frame(notebook, padding="10")
        notebook.add(nvram_frame, text="NVRAM Tools")
        
        ttk.Label(nvram_frame, text="Instant operations (no BIOS flash required):").grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        ttk.Button(nvram_frame, text="Check NVRAM Access", command=self._nvram_report).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Button(nvram_frame, text="Unlock via NVRAM", command=self._nvram_unlock).grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=5)
        
        ttk.Button(nvram_frame, text="Backup Setup", command=self._nvram_backup).grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Button(nvram_frame, text="Restore Setup", command=self._nvram_restore).grid(row=2, column=1, sticky=tk.W, pady=(5, 0), padx=5)
        
        # Tab 5: Flash Tools
        flash_frame = ttk.Frame(notebook, padding="10")
        notebook.add(flash_frame, text="Flash Tools")
        
        ttk.Label(flash_frame, text="Direct BIOS flashing:").grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        ttk.Button(flash_frame, text="Detect Flash Tools", command=self._flash_detect).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        self.flash_after_patch_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(flash_frame, text="Flash after patching", variable=self.flash_after_patch_var).grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        
        # Log output area
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="10")
        log_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Connect log handler to text widget
        self.log_handler.set_text_widget(self.log_text)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(button_frame, text="Dry Run", command=self._dry_run).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Patch BIOS", command=self._patch_bios).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Log", command=self._clear_log).pack(side=tk.RIGHT, padx=5)
    
    def _browse_input(self):
        """Browse for input BIOS file."""
        filename = filedialog.askopenfilename(
            title="Select Input BIOS",
            filetypes=[("BIOS files", "*.bin *.rom *.cap *.fd"), ("All files", "*.*")]
        )
        if filename:
            self.input_file = filename
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filename)
            
            # Auto-set output filename
            if not self.output_file:
                output = str(Path(filename).with_name(Path(filename).stem + "_MOD.bin"))
                self.output_file = output
                self.output_entry.delete(0, tk.END)
                self.output_entry.insert(0, output)
    
    def _browse_output(self):
        """Browse for output BIOS file."""
        filename = filedialog.asksaveasfilename(
            title="Select Output BIOS",
            filetypes=[("BIOS files", "*.bin"), ("All files", "*.*")],
            defaultextension=".bin"
        )
        if filename:
            self.output_file = filename
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, filename)
    
    def _apply_preset(self):
        """Apply selected preset."""
        preset_name = self.preset_var.get()
        if not preset_name:
            return
        
        try:
            self.config = get_preset(preset_name)
            
            # Update UI with preset values
            if self.config.pl1:
                self.pl1_var.set(self.config.pl1)
            if self.config.pl2:
                self.pl2_var.set(self.config.pl2)
            if self.config.tau:
                self.tau_var.set(self.config.tau)
            if self.config.vcore_offset is not None:
                self.vcore_var.set(self.config.vcore_offset)
            if self.config.ring_offset is not None:
                self.ring_var.set(self.config.ring_offset)
            if self.config.sa_offset is not None:
                self.sa_var.set(self.config.sa_offset)
            if self.config.io_offset is not None:
                self.io_var.set(self.config.io_offset)
            
            self.cfg_unlock_var.set(self.config.cfg_lock == 0)
            self.oc_unlock_var.set(self.config.oc_lock == 0)
            
            if self.config.above_4g is not None:
                self.above_4g_var.set(self.config.above_4g == 1)
            if self.config.resizable_bar is not None:
                self.rebar_var.set(self.config.resizable_bar == 1)
            if self.config.me_disable is not None:
                self.me_disable_var.set(self.config.me_disable == 1)
            
            logging.info(f"Applied preset: {preset_name}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply preset: {e}")
    
    def _collect_config(self) -> BIOSConfig:
        """Collect configuration from UI."""
        config = BIOSConfig()
        
        config.pl1 = self.pl1_var.get()
        config.pl2 = self.pl2_var.get()
        config.tau = self.tau_var.get()
        
        config.vcore_offset = self.vcore_var.get()
        config.ring_offset = self.ring_var.get()
        config.sa_offset = self.sa_var.get()
        config.io_offset = self.io_var.get()
        
        config.cfg_lock = 0 if self.cfg_unlock_var.get() else 1
        config.oc_lock = 0 if self.oc_unlock_var.get() else 1
        
        config.above_4g = 1 if self.above_4g_var.get() else 0
        config.resizable_bar = 1 if self.rebar_var.get() else 0
        config.me_disable = 1 if self.me_disable_var.get() else 0
        
        return config
    
    def _dry_run(self):
        """Perform dry run."""
        if not self.input_file:
            messagebox.showerror("Error", "Please select an input BIOS file")
            return
        
        def run():
            try:
                logging.info("=== DRY RUN ===")
                logging.info(f"Input: {self.input_file}")
                
                config = self._collect_config()
                
                engine = PatchEngine(verbose=True)
                
                if not engine.load(self.input_file):
                    return
                
                if engine.parser.setup_offset:
                    engine.apply_config(config)
                
                engine.print_summary()
                
                logging.info("=== DRY RUN COMPLETE (No files modified) ===")
            
            except Exception as e:
                logging.error(f"Dry run error: {e}")
                messagebox.showerror("Error", str(e))
        
        # Run in thread to not block UI
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def _patch_bios(self):
        """Patch BIOS file."""
        if not self.input_file:
            messagebox.showerror("Error", "Please select an input BIOS file")
            return
        
        if not self.output_file:
            messagebox.showerror("Error", "Please select an output BIOS file")
            return
        
        def run():
            try:
                logging.info("=== PATCHING BIOS ===")
                logging.info(f"Input: {self.input_file}")
                logging.info(f"Output: {self.output_file}")
                
                config = self._collect_config()
                
                engine = PatchEngine(verbose=True)
                
                if not engine.load(self.input_file):
                    messagebox.showerror("Error", "Failed to load BIOS")
                    return
                
                if not engine.preflight(force=False):
                    response = messagebox.askyesno("Warning", 
                        "Preflight checks failed. Continue anyway? (Risky!)")
                    if not response:
                        return
                
                if engine.parser.setup_offset:
                    engine.apply_config(config)
                
                if not engine.save(self.output_file):
                    messagebox.showerror("Error", "Failed to save modded BIOS")
                    return
                
                engine.print_summary()
                
                logging.info(f"✓ Success! Modded BIOS saved to: {self.output_file}")
                
                # Flash if requested
                if self.flash_after_patch_var.get():
                    self._flash_bios(self.output_file)
                else:
                    messagebox.showinfo("Success", f"BIOS patched successfully!\n\nOutput: {self.output_file}")
            
            except Exception as e:
                logging.error(f"Patching error: {e}")
                messagebox.showerror("Error", str(e))
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def _flash_bios(self, bios_file: str):
        """Flash BIOS file."""
        response = messagebox.askyesno("Confirm Flash",
            "⚠️  WARNING ⚠️\n\n"
            "This will modify your system BIOS!\n\n"
            "Ensure you have:\n"
            "- A working backup\n"
            "- Stable power supply\n"
            "- Recovery method ready\n\n"
            "Continue with flash?")
        
        if not response:
            return
        
        try:
            flasher = Flasher()
            
            if not flasher.is_available():
                messagebox.showerror("Error", "No flash tool available")
                return
            
            data = Path(bios_file).read_bytes()
            
            if flasher.flash(data, verify=True):
                messagebox.showinfo("Success", 
                    "Flash completed successfully!\n\n"
                    "⚠️  REBOOT REQUIRED to apply changes")
            else:
                messagebox.showerror("Error", "Flash operation failed")
        
        except Exception as e:
            logging.error(f"Flash error: {e}")
            messagebox.showerror("Error", str(e))
    
    def _nvram_report(self):
        """Show NVRAM access report."""
        from ..nvram import print_nvram_report
        print_nvram_report()
    
    def _nvram_unlock(self):
        """Unlock via NVRAM."""
        def run():
            try:
                unlocker = NVRAMUnlocker()
                results = unlocker.nv_unlock(dry=False)
                
                success = sum(1 for _, ok, _ in results if ok)
                
                msg = f"NVRAM Unlock Results:\n\n"
                for name, ok, message in results:
                    status = "✓" if ok else "✗"
                    msg += f"{status} {name}: {message}\n"
                
                msg += f"\nSuccessful: {success}/{len(results)}"
                
                if success > 0:
                    msg += "\n\n⚠️  Reboot required for changes to take effect"
                    messagebox.showinfo("NVRAM Unlock", msg)
                else:
                    messagebox.showerror("NVRAM Unlock Failed", msg)
            
            except Exception as e:
                logging.error(f"NVRAM unlock error: {e}")
                messagebox.showerror("Error", str(e))
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def _nvram_backup(self):
        """Backup Setup via NVRAM."""
        filename = filedialog.asksaveasfilename(
            title="Save Setup Backup",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")],
            defaultextension=".bin"
        )
        
        if filename:
            try:
                nvram = NVRAMAccess()
                if nvram.backup_setup(filename):
                    messagebox.showinfo("Success", f"Setup backed up to:\n{filename}")
                else:
                    messagebox.showerror("Error", "Failed to backup Setup")
            except Exception as e:
                messagebox.showerror("Error", str(e))
    
    def _nvram_restore(self):
        """Restore Setup via NVRAM."""
        filename = filedialog.askopenfilename(
            title="Select Setup Backup",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        
        if filename:
            response = messagebox.askyesno("Confirm Restore",
                "This will restore Setup from backup.\n\n"
                "Continue?")
            
            if response:
                try:
                    nvram = NVRAMAccess()
                    if nvram.restore_setup(filename):
                        messagebox.showinfo("Success", 
                            "Setup restored successfully!\n\n"
                            "⚠️  Reboot recommended")
                    else:
                        messagebox.showerror("Error", "Failed to restore Setup")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
    
    def _flash_detect(self):
        """Detect available flash tools."""
        detector = FlashDetector()
        detector.print_report()
    
    def _clear_log(self):
        """Clear log output."""
        self.log_text.delete(1.0, tk.END)
    
    def run(self):
        """Run the GUI application."""
        logging.info("G5 CIA Ultimate v2.0 - BIOS Modding Toolkit")
        logging.info("=" * 60)
        self.root.mainloop()


class GUILogHandler(logging.Handler):
    """Custom log handler to redirect to GUI text widget."""
    
    def __init__(self):
        super().__init__()
        self.text_widget: Optional[scrolledtext.ScrolledText] = None
        
    def set_text_widget(self, widget: scrolledtext.ScrolledText):
        """Set the text widget to write to."""
        self.text_widget = widget
    
    def emit(self, record):
        """Emit a log record."""
        if self.text_widget:
            msg = self.format(record)
            
            # Thread-safe update
            self.text_widget.after(0, self._append_text, msg + '\n')
    
    def _append_text(self, text: str):
        """Append text to widget."""
        if self.text_widget:
            self.text_widget.insert(tk.END, text)
            self.text_widget.see(tk.END)
