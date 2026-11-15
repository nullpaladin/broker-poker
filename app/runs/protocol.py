"""Child -> worker events: stdout lines prefixed with RS + 'BP '. Everything else is log text."""
import json

PREFIX = "\x1eBP "
EXIT_NEEDS_HUMAN = 75


def encode(event: dict) -> str:
    return PREFIX + json.dumps(event)


def decode(line: str):
    """Return the event dict, or None if this is an ordinary log line."""
    if line.startswith(PREFIX):
        try:
            return json.loads(line[len(PREFIX):])
        except ValueError:
            return None
    return None
