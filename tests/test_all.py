import os
import socket
import sys
import threading
import time
import unittest
import requests
import uvicorn

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.server import app
from server.config import settings


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestProjectIYALMonolith(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _find_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        config = uvicorn.Config(app, host="127.0.0.1", port=cls.port, log_level="warning")
        cls.server = uvicorn.Server(config)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()

        # Wait for server startup (including model initialization)
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                r = requests.get(f"{cls.base_url}/api/v1/health", timeout=2)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Server failed to start within 60 seconds")

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=5)

    def test_01_public_and_admin_html_routes(self):
        r1 = requests.get(f"{self.base_url}/")
        self.assertEqual(r1.status_code, 200)
        self.assertIn("இயல் (IYAL)", r1.text)
        self.assertIn('id="researchgate-btn"', r1.text)

        cfg_res = requests.get(f"{self.base_url}/api/v1/public-config")
        self.assertEqual(cfg_res.status_code, 200)
        self.assertIn("researchgate_paper_url", cfg_res.json())
        self.assertTrue(cfg_res.json()["researchgate_paper_url"].startswith("http"))

        r2 = requests.get(f"{self.base_url}/admin")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("Admin Portal", r2.text)

        r3 = requests.get(f"{self.base_url}/api/v1/health")
        self.assertEqual(r3.status_code, 200)
        data = r3.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("classifier", data["models"])
        self.assertIn("standardizer", data["models"])

    def test_02_step6_and_step7_legacy_font_detection_and_preview(self):
        sample = "Kaalai வணkkam உலகம் cyfk; Moratuwa."
        r = requests.post(
            f"{self.base_url}/api/v1/detect-encoding",
            json={"input_text": sample, "protected_words": ["Moratuwa"]},
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["requires_confirmation"])
        self.assertEqual(data["encoding"], "bamini2utf8")
        self.assertTrue(
            any(
                s["word"] == "cyfk;" and s["preview_unicode"] == "உலகம்"
                for s in data["legacy_samples"]
            )
        )

    def test_03_full_11_step_normalization_pipeline(self):
        sample = "Kaalai வணkkam உலகம் cyfk; Moratuwa."
        r = requests.post(
            f"{self.base_url}/api/v1/analyze",
            json={
                "input_text": sample,
                "encoding": "bamini2utf8",
                "need_translation": False,
                "colloquial_to_standard": False,
                "protected_words": ["Moratuwa"],
            },
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("உலகம்", data["output"])
        self.assertIn("Moratuwa", data["output"])
        tokens = data["result"][0]["results"]
        type_by_word = {t["inputWord"]: t["inputType"] for t in tokens}
        self.assertEqual(type_by_word["வணkkam"], "en_tamil")
        self.assertEqual(type_by_word["உலகம்"], "raw_tamil")
        self.assertEqual(type_by_word["cyfk;"], "Legacy Font Encoding")
        self.assertEqual(type_by_word["Moratuwa"], "protected_en")

        # Test Step 10: English-to-Tamil translation with inflected words & protected word preservation
        r_trans = requests.post(
            f"{self.base_url}/api/v1/analyze",
            json={
                "input_text": "Vanakkam! I am translating English words for students in Moratuwa.",
                "encoding": "legacy_font_not_found",
                "need_translation": True,
                "colloquial_to_standard": False,
                "protected_words": ["Moratuwa"],
            },
        )
        self.assertEqual(r_trans.status_code, 200)
        trans_data = r_trans.json()
        self.assertIn("Moratuwa", trans_data["output"])
        sent2_tokens = trans_data["result"][1]["results"]
        self.assertTrue(any(t["inputType"] == "en_translated" for t in sent2_tokens))
        self.assertTrue(any(t["inputType"] == "protected_en" and t["output"] == "Moratuwa" for t in sent2_tokens))

    def test_04_colloquial_to_standard_model(self):
        r = requests.post(
            f"{self.base_url}/api/v1/colloquial-to-standard",
            json={"input_text": "என்ன பண்றீங்க"},
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(len(data["standard_tamil"]) > 0)

    def test_05_public_feedback_submission(self):
        r = requests.post(
            f"{self.base_url}/api/v1/feedback",
            json={
                "category": "classification",
                "rating": 5,
                "input_text": "cyfk;",
                "output": {"output": "உலகம்"},
                "feedback": "Bamini detection worked accurately!",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["success"])

    def test_06_superadmin_auth_gmail_invite_and_rbac(self):
        # 1. Login as predefined superadmin
        login_res = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "identifier": settings.SUPERADMIN_USERNAME,
                "password": settings.SUPERADMIN_PASSWORD,
            },
        )
        self.assertEqual(login_res.status_code, 200)
        super_token = login_res.json()["access_token"]
        super_headers = {"Authorization": f"Bearer {super_token}"}

        # 2. Invite a new admin via Gmail
        test_gmail = "invited.researcher@gmail.com"
        users_res = requests.get(
            f"{self.base_url}/api/v1/admin/users", headers=super_headers
        )
        for u in users_res.json()["users"]:
            if u["email"] == test_gmail:
                requests.delete(
                    f"{self.base_url}/api/v1/admin/users/{u['id']}",
                    headers=super_headers,
                )

        inv_res = requests.post(
            f"{self.base_url}/api/v1/admin/users/invite",
            headers=super_headers,
            json={"email": test_gmail, "role": "admin"},
        )
        self.assertEqual(inv_res.status_code, 200)
        invite_data = inv_res.json()["user"]
        invite_token = invite_data["invite_token"]
        invited_user_id = invite_data["id"]

        # 3. Invited Gmail admin accepts invite & sets password
        accept_res = requests.post(
            f"{self.base_url}/api/v1/auth/accept-invite",
            json={
                "email": test_gmail,
                "invite_token": invite_token,
                "new_password": "InvitedAdminPassword123!",
            },
        )
        self.assertEqual(accept_res.status_code, 200)
        admin_token = accept_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 4. Verify regular admin CAN access feedback and models
        fb_list = requests.get(
            f"{self.base_url}/api/v1/admin/feedback", headers=admin_headers
        )
        self.assertEqual(fb_list.status_code, 200)
        self.assertGreaterEqual(fb_list.json()["summary"]["total"], 1)

        models_res = requests.get(
            f"{self.base_url}/api/v1/admin/models", headers=admin_headers
        )
        self.assertEqual(models_res.status_code, 200)

        # 5. Verify regular admin CANNOT manage users (403 Forbidden)
        forbidden_res = requests.get(
            f"{self.base_url}/api/v1/admin/users", headers=admin_headers
        )
        self.assertEqual(forbidden_res.status_code, 403)

        # 6. Test model diagnostic endpoint
        test_clf = requests.post(
            f"{self.base_url}/api/v1/admin/models/classifier/test",
            headers=admin_headers,
            json={"sample_input": "tzf;fk;"},
        )
        self.assertEqual(test_clf.status_code, 200)
        self.assertEqual(test_clf.json()["sample_output"], "Legacy Font Encoding")

        # 7. Superadmin deletes the test invited admin
        del_res = requests.delete(
            f"{self.base_url}/api/v1/admin/users/{invited_user_id}",
            headers=super_headers,
        )
        self.assertEqual(del_res.status_code, 200)

    def test_07_brute_force_protection_and_observability(self):
        dummy_id = "attacker_test@gmail.com"
        for _ in range(settings.MAX_LOGIN_ATTEMPTS):
            r = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"identifier": dummy_id, "password": "wrongpassword"},
            )
            self.assertEqual(r.status_code, 401)

        # Next attempt must be blocked with 429 Too Many Requests
        locked_res = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"identifier": dummy_id, "password": "wrongpassword"},
        )
        self.assertEqual(locked_res.status_code, 429)

        # Clear IP lockout via security engine so superadmin can query observability
        from server.security import security_engine

        security_engine.unban_ip("127.0.0.1")
        security_engine.record_login_success("127.0.0.1", dummy_id)

        login_res = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "identifier": settings.SUPERADMIN_USERNAME,
                "password": settings.SUPERADMIN_PASSWORD,
            },
        )
        super_token = login_res.json()["access_token"]
        obs_res = requests.get(
            f"{self.base_url}/api/v1/admin/observability",
            headers={"Authorization": f"Bearer {super_token}"},
        )
        self.assertEqual(obs_res.status_code, 200)
        obs_data = obs_res.json()
        self.assertIn("system", obs_data)
        self.assertIn("security", obs_data)
        self.assertIn("audit_logs", obs_data)
        self.assertIn("app_logs", obs_data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
