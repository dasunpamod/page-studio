#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PageStudio Windowed Launcher
Double-click to run PageStudio directly without opening a terminal window.
"""
import sys
import os

# Ensure project directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import main

if __name__ == "__main__":
    main()
