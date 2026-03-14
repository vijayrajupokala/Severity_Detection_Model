#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import threading
import webbrowser

def open_browser():
    try:
        webbrowser.open("http://127.0.0.1:8000/")
    except Exception:
        pass

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_django.settings')
    
    # Suppress TensorFlow logging and warnings to keep the terminal clean
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    
    # Automatically add runserver if executed with no arguments (e.g., double clicking)
    if len(sys.argv) == 1:
        sys.argv.extend(['runserver', '127.0.0.1:8000'])
        
    # If starting runserver natively or without explicit IP/Port, force it to 127.0.0.1:8000
    # to avoid the Windows Defender Firewall prompt ('Office permissions')
    if 'runserver' in sys.argv and ('127.0.0.1:8000' not in sys.argv):
        try:
            sys.argv.append('127.0.0.1:8000')
        except Exception:
            pass

    # Open browser on the main thread (checking RUN_MAIN to avoid doing it twice in autoreload)
    if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
        threading.Timer(1.25, open_browser).start()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
