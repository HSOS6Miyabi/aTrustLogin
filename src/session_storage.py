"""JSON-backed persistence for aTrust browser session state."""

import json
import os
import tempfile

SESSION_FILENAME = "ATrustLoginStorage.json"


def read_session(data_dir):
    """Read session state without executing data from the storage file."""
    with open(os.path.join(data_dir, SESSION_FILENAME), "r", encoding="utf-8") as stream:
        return json.load(stream)


def write_session(data_dir, data):
    """Atomically replace session state using a private temporary file."""
    os.makedirs(data_dir, mode=0o700, exist_ok=True)
    destination = os.path.join(data_dir, SESSION_FILENAME)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=data_dir,
            prefix=".atrust-session-", delete=False
        ) as stream:
            temporary_path = stream.name
            json.dump(data, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)
