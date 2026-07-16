import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import store
import session_manager


class TestHITLAndSessions(unittest.TestCase):
    def setUp(self):
        # Clear stores
        store._hitl_pauses.clear()
        # Mock file system inside session_manager to avoid side effects
        self.temp_session_dir = os.path.join(BACKEND_DIR, "test_cookies")
        os.makedirs(self.temp_session_dir, exist_ok=True)
        session_manager.SESSION_DIR = self.temp_session_dir

    def tearDown(self):
        # Clean up temporary test session directory
        import shutil
        if os.path.exists(self.temp_session_dir):
            shutil.rmtree(self.temp_session_dir)

    def test_url_to_platform(self):
        self.assertEqual(session_manager.url_to_platform("https://www.naukri.com/job/123"), "naukri")
        self.assertEqual(session_manager.url_to_platform("https://linkedin.com/jobs/view/456"), "linkedin")
        self.assertEqual(session_manager.url_to_platform("https://indeed.com/viewjob?jk=789"), "indeed")
        self.assertEqual(session_manager.url_to_platform("https://unknown-platform.com/job"), None)

    def test_hitl_pause_and_signal_flow(self):
        task_id = "test-task-hitl"
        # 1. Register pause
        pause_state = store.hitl_pause(
            task_id=task_id,
            reason="OTP required",
            platform="naukri",
            current_url="https://naukri.com/login",
            screenshot_path="/path/to/screenshot.png"
        )
        self.assertEqual(pause_state.task_id, task_id)
        self.assertEqual(pause_state.reason, "OTP required")
        self.assertEqual(pause_state.signal, "waiting")

        # 2. Get signal state
        self.assertEqual(store.hitl_get_signal(task_id), "waiting")

        # 3. Send signal
        success = store.hitl_signal(task_id, "continue")
        self.assertTrue(success)
        self.assertEqual(store.hitl_get_signal(task_id), "continue")

        # 4. Clear signal
        store.hitl_clear(task_id)
        self.assertIsNone(store.hitl_get_pause(task_id))

    def test_session_manager_save_and_load(self):
        # Mock Playwright context and page
        context = MagicMock()
        context.cookies = AsyncMock(return_value=[
            {"name": "session_id", "value": "xyz123", "domain": ".naukri.com", "path": "/", "expires": 1893456000}
        ])

        page = MagicMock()
        page.evaluate = AsyncMock(side_effect=[
            {"user_theme": "dark"},  # localStorage
            {"tab_id": "999"}        # sessionStorage
        ])

        # Save session
        import asyncio
        session_data = asyncio.run(
            session_manager.save_session_from_browser(context, page, "naukri")
        )

        self.assertEqual(session_data["platform"], "naukri")
        self.assertEqual(len(session_data["cookies"]), 1)
        self.assertEqual(session_data["local_storage"]["user_theme"], "dark")

        # Verify validation
        valid, loaded = session_manager.is_session_valid("naukri")
        self.assertTrue(valid)
        self.assertEqual(loaded["platform"], "naukri")

        # Increment count
        session_manager.increment_session_app_count("naukri")
        valid, loaded = session_manager.is_session_valid("naukri")
        self.assertEqual(loaded["applications_count"], 1)

        # Clear session
        session_manager.clear_session("naukri")
        self.assertIsNone(session_manager.get_session("naukri"))


if __name__ == "__main__":
    unittest.main()
