#!/usr/bin/env python3
"""Run from the repo root: python -m app.manage <command>"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.brokerpoker.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
