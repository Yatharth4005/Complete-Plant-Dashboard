#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
       
    # If no arguments are provided, default to starting the server on 0.0.0.0:4321
    if len(sys.argv) == 1:
        sys.argv.extend(['runserver', '172.17.18.13:4321'])
        
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
