#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import site
import sys
from pathlib import Path


def main():
    """Run administrative tasks."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    candidate_sites = []
    try:
        candidate_sites.append(site.getusersitepackages())
    except Exception:
        pass
    candidate_sites.append(str(Path.home() / "AppData" / "Roaming" / "Python" / "Python313" / "site-packages"))
    users_root = Path("C:/Users")
    if users_root.exists():
        for user_dir in users_root.iterdir():
            candidate_sites.append(str(user_dir / "AppData" / "Roaming" / "Python" / "Python313" / "site-packages"))
    for candidate in candidate_sites:
        if candidate and os.path.isdir(candidate):
            site.addsitedir(candidate)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
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
