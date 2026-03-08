import http.client
import os
import re
import threading
import unittest
from http import HTTPStatus
from http.server import ThreadingHTTPServer

from app.skeleton_server import SkeletonHandler


class AuthFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["WATCHDOG_PASSWORD"] = "test-password"
        os.environ["SESSION_SIGNING_SECRET"] = "test-signing-secret"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), SkeletonHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        payload = response.read()
        header_items = response.getheaders()
        conn.close()
        return response.status, header_items, payload

    def _extract_cookie(self, headers, name):
        prefix = f"{name}="
        for header, value in headers:
            if header.lower() == "set-cookie" and value.startswith(prefix):
                return value.split(";", 1)[0]
        return ""

    def _login(self):
        status, headers, body = self.request("GET", "/login")
        self.assertEqual(status, HTTPStatus.OK)
        csrf_cookie = self._extract_cookie(headers, "pw_csrf")
        self.assertTrue(csrf_cookie)
        token_match = re.search(rb'name="csrf_token" value="([^"]+)"', body)
        self.assertIsNotNone(token_match)
        csrf_token = token_match.group(1).decode("utf-8")

        form = f"password=test-password&csrf_token={csrf_token}".encode("utf-8")
        status, headers, _ = self.request(
            "POST",
            "/login",
            body=form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": csrf_cookie,
            },
        )
        self.assertEqual(status, HTTPStatus.FOUND)
        session_cookie = self._extract_cookie(headers, "pw_session")
        self.assertTrue(session_cookie)
        new_csrf_cookie = self._extract_cookie(headers, "pw_csrf")
        self.assertTrue(new_csrf_cookie)
        return session_cookie, new_csrf_cookie

    def test_main_page_redirects_to_login_without_cookie(self):
        status, headers, _ = self.request("GET", "/")
        self.assertEqual(status, HTTPStatus.FOUND)
        self.assertIn(("Location", "/login"), headers)

    def test_csrf_is_required_for_post_and_logout_clears_session(self):
        session_cookie, csrf_cookie = self._login()
        cookie_header = f"{session_cookie}; {csrf_cookie}"

        status, _, _ = self.request(
            "POST",
            "/logout",
            headers={"Cookie": cookie_header},
        )
        self.assertEqual(status, HTTPStatus.FORBIDDEN)

        csrf_value = csrf_cookie.split("=", 1)[1]
        status, headers, _ = self.request(
            "POST",
            "/logout",
            headers={
                "Cookie": cookie_header,
                "X-CSRF-Token": csrf_value,
            },
        )
        self.assertEqual(status, HTTPStatus.FOUND)
        self.assertIn(("Location", "/login"), headers)
        expired_session = self._extract_cookie(headers, "pw_session")
        self.assertTrue(expired_session.endswith("="))

    def test_login_sets_session_cookie(self):
        session_cookie, _ = self._login()
        self.assertTrue(session_cookie.startswith("pw_session="))


if __name__ == "__main__":
    unittest.main()
