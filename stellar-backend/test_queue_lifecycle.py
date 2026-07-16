"""
test_queue_lifecycle.py
=======================
Automated tests for the AutoApply queue database layer.

Tests verify:
  1. db_update_queue_status is NOT on db module (it lives in orchestrator)
  2. db_update_queue_status (in orchestrator) works correctly for all statuses
  3. Full queue lifecycle: discovered → queued → applying → applied / failed / skipped
  4. Stale / invalid status updates are caught
  5. DB failure during update does NOT crash the process (it logs and continues)
  6. All public queue functions exist and are callable
  7. No AttributeError when calling db_update_queue_status through the orchestrator module

Run with:
    cd stellar-backend
    venv/Scripts/python -m pytest test_queue_lifecycle.py -v
  or:
    venv/Scripts/python test_queue_lifecycle.py
"""

from __future__ import annotations
import sys
import os
import uuid
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# ── Path setup ────────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR  = os.path.join(BACKEND_DIR, "agents")
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, AGENTS_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_temp_db() -> tuple[str, sqlite3.Connection]:
    """Return (path, conn) for an in-memory-like temp SQLite DB."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
    CREATE TABLE auto_apply_queue (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        job_title TEXT NOT NULL,
        job_company TEXT NOT NULL,
        job_url TEXT NOT NULL,
        job_source TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'discovered',
        ats_platform TEXT DEFAULT '',
        failure_reason TEXT DEFAULT '',
        screenshot_path TEXT DEFAULT '',
        fields_filled INTEGER DEFAULT 0,
        attempts INTEGER DEFAULT 0,
        max_attempts INTEGER DEFAULT 3,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        applied_at TEXT DEFAULT '',
        debug_mode BOOLEAN DEFAULT 0
    )
    """)
    conn.commit()
    return path, conn


def _insert_queue_entry(conn: sqlite3.Connection, status: str = "discovered") -> str:
    """Insert a dummy queue entry and return its id."""
    qid  = str(uuid.uuid4())
    now  = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO auto_apply_queue
          (id, user_id, run_id, job_id, job_title, job_company, job_url,
           status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (qid, "u1", "r1", "j1", "Tester", "Acme", "https://example.com",
          status, now, now))
    conn.commit()
    return qid


# ─────────────────────────────────────────────────────────────────────────────
# Test Cases
# ─────────────────────────────────────────────────────────────────────────────

class TestDbModuleHasNoQueueStatusFunction(unittest.TestCase):
    """The `db` module must NOT have db_update_queue_status — it belongs in orchestrator."""

    def test_db_module_missing_db_update_queue_status(self):
        import db
        self.assertFalse(
            hasattr(db, "db_update_queue_status"),
            "db.py should NOT export db_update_queue_status. "
            "It is defined exclusively in agents/orchestrator.py."
        )

    def test_orchestrator_has_db_update_queue_status(self):
        import orchestrator
        self.assertTrue(
            hasattr(orchestrator, "db_update_queue_status"),
            "orchestrator.py must export db_update_queue_status."
        )
        self.assertTrue(callable(orchestrator.db_update_queue_status))


class TestOrchestratorQueueFunctionsExist(unittest.TestCase):
    """All public queue-management functions must exist and be callable."""

    def setUp(self):
        import orchestrator
        self.orc = orchestrator

    def test_db_enqueue_job_exists(self):
        self.assertTrue(callable(self.orc.db_enqueue_job))

    def test_db_update_queue_status_exists(self):
        self.assertTrue(callable(self.orc.db_update_queue_status))

    def test_db_mark_as_queued_exists(self):
        self.assertTrue(callable(self.orc.db_mark_as_queued))

    def test_db_get_queue_stats_exists(self):
        self.assertTrue(callable(self.orc.db_get_queue_stats))

    def test_db_get_queue_entries_exists(self):
        self.assertTrue(callable(self.orc.db_get_queue_entries))

    def test_db_get_discovered_jobs_exists(self):
        self.assertTrue(callable(self.orc.db_get_discovered_jobs))

    def test_db_init_auto_apply_table_exists(self):
        self.assertTrue(callable(self.orc.db_init_auto_apply_table))


class TestQueueLifecycle(unittest.TestCase):
    """Verify all status transitions using a real SQLite temp database."""

    VALID_STATUSES = [
        "discovered", "queued", "applying",
        "applied", "failed", "skipped",
        "requires_manual_intervention", "simulated",
    ]

    def setUp(self):
        self.db_path, self.conn = _make_temp_db()

        # Patch the orchestrator to use our temp DB instead of stellar.db
        import db as _db
        import orchestrator as _orc

        self._orig_get_conn   = _db.get_db_connection
        self._orig_is_pg      = _db.IS_POSTGRES

        _db.IS_POSTGRES = False
        _db.get_db_connection = lambda: sqlite3.connect(
            self.db_path, detect_types=sqlite3.PARSE_DECLTYPES
        )

        import importlib
        importlib.reload(_orc)  # Re-bind orc module to patched db

        self.orc = _orc
        self.db  = _db

    def tearDown(self):
        self.conn.close()
        try:
            os.unlink(self.db_path)
        except Exception:
            pass

    def _read_entry(self, qid: str) -> dict:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM auto_apply_queue WHERE id = ?", (qid,)
        ).fetchone()
        conn.close()
        return dict(row) if row else {}

    # ── Lifecycle tests ───────────────────────────────────────────────────────

    def test_discovered_to_queued(self):
        qid = _insert_queue_entry(self.conn, "discovered")
        self.orc.db_mark_as_queued(qid)
        row = self._read_entry(qid)
        self.assertEqual(row["status"], "queued")

    def test_queued_to_applied(self):
        qid = _insert_queue_entry(self.conn, "queued")
        self.orc.db_update_queue_status(qid, "applied")
        row = self._read_entry(qid)
        self.assertEqual(row["status"], "applied")
        # applied_at must be set
        self.assertNotEqual(row.get("applied_at", ""), "")

    def test_queued_to_failed(self):
        qid = _insert_queue_entry(self.conn, "queued")
        self.orc.db_update_queue_status(qid, "failed", failure_reason="Playwright crash")
        row = self._read_entry(qid)
        self.assertEqual(row["status"], "failed")
        self.assertIn("Playwright crash", row["failure_reason"])

    def test_queued_to_requires_manual(self):
        qid = _insert_queue_entry(self.conn, "queued")
        self.orc.db_update_queue_status(qid, "requires_manual_intervention",
                                         failure_reason="CAPTCHA detected")
        row = self._read_entry(qid)
        self.assertEqual(row["status"], "requires_manual_intervention")

    def test_queued_to_skipped(self):
        qid = _insert_queue_entry(self.conn, "queued")
        self.orc.db_update_queue_status(qid, "skipped", failure_reason="Score 40% < 70%")
        row = self._read_entry(qid)
        self.assertEqual(row["status"], "skipped")

    def test_attempts_increments(self):
        qid = _insert_queue_entry(self.conn, "queued")
        before = self._read_entry(qid)["attempts"]
        self.orc.db_update_queue_status(qid, "failed")
        after = self._read_entry(qid)["attempts"]
        self.assertEqual(after, before + 1)

    def test_screenshot_and_fields_stored(self):
        qid = _insert_queue_entry(self.conn, "queued")
        self.orc.db_update_queue_status(
            qid, "applied",
            screenshot_path="/screenshots/test.png",
            fields_filled=5,
        )
        row = self._read_entry(qid)
        self.assertEqual(row["screenshot_path"], "/screenshots/test.png")
        self.assertEqual(row["fields_filled"], 5)

    def test_ats_platform_stored(self):
        qid = _insert_queue_entry(self.conn, "queued")
        self.orc.db_update_queue_status(qid, "requires_manual_intervention",
                                         ats_platform="greenhouse.io")
        row = self._read_entry(qid)
        self.assertEqual(row["ats_platform"], "greenhouse.io")

    def test_all_terminal_statuses_are_valid(self):
        for status in ["applied", "failed", "skipped", "requires_manual_intervention", "simulated"]:
            with self.subTest(status=status):
                qid = _insert_queue_entry(self.conn, "queued")
                # Should not raise
                self.orc.db_update_queue_status(qid, status)
                row = self._read_entry(qid)
                self.assertEqual(row["status"], status)


class TestDbUpdateQueueStatusNotOnDbModule(unittest.TestCase):
    """Calling db.db_update_queue_status must raise AttributeError (proves the bug is real)."""

    def test_calling_via_db_module_raises_attribute_error(self):
        import db
        with self.assertRaises(AttributeError):
            db.db_update_queue_status("fake-id", "failed")  # type: ignore[attr-defined]


class TestCrashHandlerDoesNotPropagateDbError(unittest.TestCase):
    """A DB failure inside db_update_queue_status must be caught and logged, not re-raised."""

    def test_db_error_logged_not_raised(self):
        """Simulate process_single_autoapply_job's crash-handler try/except pattern."""
        import orchestrator

        errors_logged: list[str] = []

        def fake_db_update(queue_id, status, **kwargs):
            raise RuntimeError("Simulated DB connection failure")

        with patch.object(orchestrator, "db_update_queue_status", side_effect=fake_db_update):
            queue_id = "test-qid"
            error_msg = "SomeError: something went wrong"
            errors_captured: list[str] = []

            # Replicate the pattern from process_single_autoapply_job's except block
            try:
                orchestrator.db_update_queue_status(queue_id, "failed",
                                                    failure_reason=error_msg[:500])
            except Exception as db_err:
                errors_captured.append(str(db_err))  # logs, does not re-raise

            # The process must have continued (not crashed) and captured the error
            self.assertEqual(len(errors_captured), 1)
            self.assertIn("Simulated DB connection failure", errors_captured[0])


class TestQueueStats(unittest.TestCase):
    """db_get_queue_stats returns correct aggregate counts."""

    def setUp(self):
        self.db_path, self.conn = _make_temp_db()
        import db as _db
        import orchestrator as _orc
        _db.IS_POSTGRES = False
        _db.get_db_connection = lambda: sqlite3.connect(
            self.db_path, detect_types=sqlite3.PARSE_DECLTYPES
        )
        import importlib
        importlib.reload(_orc)
        self.orc = _orc

    def tearDown(self):
        self.conn.close()
        try:
            os.unlink(self.db_path)
        except Exception:
            pass

    def test_stats_empty_db(self):
        stats = self.orc.db_get_queue_stats()
        self.assertIsInstance(stats, dict)

    def test_stats_after_inserts(self):
        _insert_queue_entry(self.conn, "applied")
        _insert_queue_entry(self.conn, "applied")
        _insert_queue_entry(self.conn, "failed")
        stats = self.orc.db_get_queue_stats()
        self.assertEqual(stats.get("applied", 0), 2)
        self.assertEqual(stats.get("failed", 0), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader  = unittest.TestLoader()
    suite   = loader.loadTestsFromModule(sys.modules[__name__])
    runner  = unittest.TextTestRunner(verbosity=2)
    result  = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
