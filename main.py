#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PageStudio - Main Entry Point
Cross-Platform Visual GUI Generator for Python Tkinter.
Supports macOS, Windows, and Linux natively with zero external dependencies.
"""

import tkinter as tk
from pagestudio import PageStudioApp


def main():
    """Initialize and run the PageStudio IDE."""
    root = tk.Tk()
    app = PageStudioApp(root)
    root.mainloop()
    return app


if __name__ == "__main__":
    main()
