"""Theme support for GUI."""

import tkinter as tk
from tkinter import ttk


def apply_theme(root: tk.Tk, theme_name: str = "default"):
    """Apply theme to GUI.
    
    Args:
        root: Root window
        theme_name: Theme name ('default', 'dark', 'light')
    """
    style = ttk.Style(root)
    
    # Try to use platform-specific themes
    available_themes = style.theme_names()
    
    if theme_name == "default":
        # Use best available theme for platform
        if 'vista' in available_themes:
            style.theme_use('vista')
        elif 'aqua' in available_themes:
            style.theme_use('aqua')
        elif 'clam' in available_themes:
            style.theme_use('clam')
        else:
            style.theme_use('default')
    
    elif theme_name == "dark":
        # Dark theme (basic implementation)
        if 'clam' in available_themes:
            style.theme_use('clam')
        
        # Configure dark colors
        root.configure(bg='#2b2b2b')
        
        style.configure('.',
            background='#2b2b2b',
            foreground='#e0e0e0',
            fieldbackground='#3c3c3c',
            bordercolor='#4a4a4a',
            darkcolor='#2b2b2b',
            lightcolor='#4a4a4a'
        )
        
        style.configure('TLabel',
            background='#2b2b2b',
            foreground='#e0e0e0'
        )
        
        style.configure('TButton',
            background='#3c3c3c',
            foreground='#e0e0e0',
            bordercolor='#4a4a4a'
        )
        
        style.map('TButton',
            background=[('active', '#4a4a4a')]
        )
        
        style.configure('TEntry',
            fieldbackground='#3c3c3c',
            foreground='#e0e0e0',
            insertcolor='#e0e0e0'
        )
        
        style.configure('TFrame',
            background='#2b2b2b'
        )
        
        style.configure('TLabelframe',
            background='#2b2b2b',
            foreground='#e0e0e0',
            bordercolor='#4a4a4a'
        )
        
        style.configure('TLabelframe.Label',
            background='#2b2b2b',
            foreground='#e0e0e0'
        )
        
        style.configure('TNotebook',
            background='#2b2b2b',
            bordercolor='#4a4a4a'
        )
        
        style.configure('TNotebook.Tab',
            background='#3c3c3c',
            foreground='#e0e0e0'
        )
        
        style.map('TNotebook.Tab',
            background=[('selected', '#4a4a4a')]
        )
    
    elif theme_name == "light":
        # Light theme (clean white)
        if 'clam' in available_themes:
            style.theme_use('clam')
        
        root.configure(bg='#ffffff')
        
        style.configure('.',
            background='#ffffff',
            foreground='#000000',
            fieldbackground='#f5f5f5',
            bordercolor='#d0d0d0'
        )
        
        style.configure('TLabel',
            background='#ffffff',
            foreground='#000000'
        )
        
        style.configure('TButton',
            background='#e8e8e8',
            foreground='#000000'
        )
        
        style.map('TButton',
            background=[('active', '#d0d0d0')]
        )
        
        style.configure('TEntry',
            fieldbackground='#ffffff',
            foreground='#000000'
        )
        
        style.configure('TFrame',
            background='#ffffff'
        )
        
        style.configure('TLabelframe',
            background='#ffffff',
            foreground='#000000'
        )
