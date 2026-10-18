"""Pytest configuration and environment setup for PageStudio."""
import os
import sys
import time

# Ensure Tkinter finds Tcl/Tk libraries on Windows with forward slashes
if sys.platform == "win32":
    tcl_lib = os.path.join(sys.prefix, "tcl", "tcl8.6")
    if os.path.exists(tcl_lib):
        os.environ["TCL_LIBRARY"] = tcl_lib
    tk_lib = os.path.join(sys.prefix, "tcl", "tk8.6")
    if os.path.exists(tk_lib):
        os.environ["TK_LIBRARY"] = tk_lib

try:
    import tkinter as tk
    import _tkinter

    _orig_tk_init = tk.Tk.__init__

    def _robust_tk_init(self, *args, **kwargs):
        for attempt in range(5):
            try:
                return _orig_tk_init(self, *args, **kwargs)
            except _tkinter.TclError as e:
                if attempt < 4:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                raise

    tk.Tk.__init__ = _robust_tk_init
except Exception:
    pass
