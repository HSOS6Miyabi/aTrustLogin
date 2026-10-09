"""Tests for private and non-executable browser session storage."""

import json
import os
import pathlib
import pickle
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from session_storage import SESSION_FILENAME, read_session, write_session


class SessionStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = pathlib.Path(self.tmp.name) / "session"

    def test_round_trip_and_replacement(self):
        original = {
            "cookies": [{"name": "tid", "value": "session-id", "httpOnly": True}],
            "local_storage": {"nonce": "quote'\\\" and 中文", "empty": ""},
        }
        write_session(str(self.data_dir), original)
        self.assertEqual(read_session(str(self.data_dir)), original)
        replacement = {"cookies": [], "local_storage": {"new": "value"}}
        write_session(str(self.data_dir), replacement)
        self.assertEqual(read_session(str(self.data_dir)), replacement)
        self.assertEqual(sorted(p.name for p in self.data_dir.iterdir()), [SESSION_FILENAME])

    def test_rejects_invalid_json(self):
        self.data_dir.mkdir()
        (self.data_dir / SESSION_FILENAME).write_text("not json", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            read_session(str(self.data_dir))

    def test_pickle_file_not_loaded(self):
        self.data_dir.mkdir()
        (self.data_dir / "ATrustLoginStorage.pkl").write_bytes(pickle.dumps({"cookies": []}))
        with self.assertRaises(FileNotFoundError):
            read_session(str(self.data_dir))

    def test_failed_serialization_preserves_previous_session(self):
        original = {"cookies": [{"name": "tid", "value": "old"}], "local_storage": {}}
        write_session(str(self.data_dir), original)
        with self.assertRaises(TypeError):
            write_session(str(self.data_dir), {"cookies": [object()], "local_storage": {}})
        self.assertEqual(read_session(str(self.data_dir)), original)
        self.assertEqual(sorted(p.name for p in self.data_dir.iterdir()), [SESSION_FILENAME])

    def test_replace_failure_preserves_previous_session_and_cleans_up(self):
        original = {"cookies": [], "local_storage": {"old": "value"}}
        write_session(str(self.data_dir), original)
        with mock.patch("session_storage.os.replace", side_effect=OSError("simulated I/O error")):
            with self.assertRaises(OSError):
                write_session(str(self.data_dir), {"cookies": [], "local_storage": {"new": "value"}})
        self.assertEqual(read_session(str(self.data_dir)), original)
        self.assertEqual(sorted(p.name for p in self.data_dir.iterdir()), [SESSION_FILENAME])

    @unittest.skipUnless(os.name == "posix", "POSIX-only permission checks")
    def test_saved_file_is_private(self):
        write_session(str(self.data_dir), {"cookies": [], "local_storage": {}})
        path = self.data_dir / SESSION_FILENAME
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.data_dir.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
