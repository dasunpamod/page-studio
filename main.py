#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PageStudio - Main Entry Point
Cross-Platform Visual GUI Generator for Python Tkinter.
Supports macOS, Windows, and Linux natively with zero external dependencies.
"""

import sys
import os
import argparse
import tkinter as tk
from pagestudio import PageStudioApp
from pagestudio.core.serializer import ProjectSerializer
from pagestudio.core.generator import CodeGenerator


def main():
    """Initialize and run the PageStudio IDE or handle CLI export."""
    parser = argparse.ArgumentParser(description="PageStudio - Modern Python GUI Builder")
    parser.add_argument("project", nargs="?", default=None, help="Path to .pgproj project file to open")
    parser.add_argument("-e", "--export", action="store_true", help="Headless export of Python code from project file")
    parser.add_argument("-o", "--output", default=".", help="Target directory for exported Python code")
    parser.add_argument("-n", "--name", default="app", help="Base name for exported application modules")

    args = parser.parse_args()

    if args.export:
        if not args.project or not os.path.exists(args.project):
            print(f"Error: Project file '{args.project}' not found for export.", file=sys.stderr)
            sys.exit(1)
        state = ProjectSerializer.load_from_file(args.project)
        os.makedirs(args.output, exist_ok=True)
        gui_path, sup_path = CodeGenerator.generate_all(state, args.name, args.output)
        print("Exported successfully:")
        print(f"  GUI:     {gui_path}")
        print(f"  Support: {sup_path}")
        return None

    root = tk.Tk()
    app = PageStudioApp(root, initial_project=args.project)
    root.mainloop()
    return app


if __name__ == "__main__":
    main()
