"""Launcher: python -m app  ->  migrate, start the local server, open the browser."""
import os
import sys
import threading
import webbrowser

PORT = int(os.environ.get("BROKER_POKER_PORT", "8000"))


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.brokerpoker.settings")
    import django
    django.setup()
    from django.core.management import call_command
    call_command("migrate", interactive=False, verbosity=0)
    from app.runs import worker
    worker.recover_interrupted()
    from waitress import serve
    from app.brokerpoker.wsgi import application
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Broker Poker is running at {url}  (Ctrl+C to stop)")
    if not os.environ.get("BROKER_POKER_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    # Bound to localhost only: this app handles personal data and has no login.
    serve(StaticFilesHandler(application), host="127.0.0.1", port=PORT, threads=8)


if __name__ == "__main__":
    sys.exit(main())
