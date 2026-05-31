from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import app_storage
import server


class ServerSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_directory = tempfile.TemporaryDirectory()
        cls.original_db_path = app_storage.DB_PATH
        app_storage.DB_PATH = Path(cls.temp_directory.name) / "reflection_agent.db"
        app_storage.init_db()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.ReflectionHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)
        app_storage.DB_PATH = cls.original_db_path
        cls.temp_directory.cleanup()

    def request(self, path: str, headers: dict[str, str] | None = None) -> urllib.request.Request:
        return urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            headers=headers or {},
            method="GET",
        )

    def test_api_rejects_missing_token(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.request("/api/analytics"), timeout=3)

        self.assertEqual(caught.exception.code, 403)

    def test_api_accepts_launch_token(self) -> None:
        request = self.request(
            "/api/analytics",
            headers={"X-Reflection-Agent-Token": server.SESSION_TOKEN},
        )

        with urllib.request.urlopen(request, timeout=3) as response:
            body = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertIn("analytics", body)

    def test_api_rejects_foreign_origin(self) -> None:
        request = self.request(
            "/api/analytics",
            headers={
                "Origin": "https://malicious.example",
                "X-Reflection-Agent-Token": server.SESSION_TOKEN,
            },
        )

        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)

        self.assertEqual(caught.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
