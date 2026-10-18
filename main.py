#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PageStudio - Main Entry Point
Cross-Platform Visual GUI Generator for Python Tkinter.
Supports macOS, Windows, and Linux natively.
"""

import sys
import tkinter as tk
from pagestudio.ui.app_window import PageStudioApp

def main():
    root = tk.Tk()
    app = PageStudioApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
