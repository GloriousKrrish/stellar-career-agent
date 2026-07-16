import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Setup path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from browser_config import BrowserConfig, get_browser_config, save_browser_config


class TestBrowserConfig(unittest.TestCase):
    def test_default_config_values(self):
        """Verify that default settings load with expected standard fallback values."""
        cfg = BrowserConfig()
        self.assertEqual(cfg.mode, "production")
        self.assertFalse(cfg.is_development)
        self.assertIsNone(cfg.browser_executable_path)
        self.assertIsNone(cfg.profile_path)
        self.assertFalse(cfg.keep_open)
        self.assertFalse(cfg.debug_logging)
        self.assertFalse(cfg.headless)
        self.assertEqual(cfg.slow_mo, 1200)

    def test_mode_derivation(self):
        """Verify derived settings like effective_headless and keep_open depend on the active mode."""
        # 1. Production Mode
        prod = BrowserConfig(mode="production", headless=True, keep_open=False)
        self.assertFalse(prod.is_development)
        self.assertTrue(prod.effective_headless)
        self.assertFalse(prod.effective_keep_open)

        # 2. Development Mode (forces headful and keep open)
        dev = BrowserConfig(mode="development", headless=True, keep_open=False)
        self.assertTrue(dev.is_development)
        self.assertFalse(dev.effective_headless)
        self.assertTrue(dev.effective_keep_open)

    def test_persistent_and_retrieval_store(self):
        """Test save_browser_config and get_browser_config using user keys."""
        user_id = "test-user-123"
        custom_cfg = BrowserConfig(
            mode="development",
            browser_executable_path="/usr/bin/custom-chrome",
            profile_path="/custom/path/to/profile",
            keep_open=True,
            debug_logging=True,
            headless=False,
            slow_mo=2000
        )

        save_browser_config(custom_cfg, user_id)
        retrieved = get_browser_config(user_id)

        self.assertEqual(retrieved.mode, "development")
        self.assertEqual(retrieved.browser_executable_path, "/usr/bin/custom-chrome")
        self.assertEqual(retrieved.profile_path, "/custom/path/to/profile")
        self.assertTrue(retrieved.keep_open)
        self.assertTrue(retrieved.debug_logging)
        self.assertFalse(retrieved.headless)
        self.assertEqual(retrieved.slow_mo, 2000)

    def test_profile_path_lock_detection(self):
        """Test lock detection heuristics for Chrome profile paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = BrowserConfig(mode="development", profile_path=tmpdir)

            # Heuristic 1: No lock file -> not in use
            in_use, msg = cfg.is_profile_in_use()
            self.assertFalse(in_use)
            self.assertEqual(msg, "")

            # Heuristic 2: Creating SingletonLock file -> in use
            lock_path = os.path.join(tmpdir, "SingletonLock")
            with open(lock_path, "w") as f:
                f.write("locked")

            in_use, msg = cfg.is_profile_in_use()
            self.assertTrue(in_use)
            self.assertIn("locked", msg)
            self.assertIn("SingletonLock", msg)


if __name__ == "__main__":
    unittest.main()
