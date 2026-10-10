"""Exercise monthly scheduling against a local remote, without AI or network."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'fitness_logs/automation/monthly_review.py'
spec = importlib.util.spec_from_file_location('monthly_review', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MonthlyReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.remote = self.root / 'remote.git'
        self.git('clone', '--quiet', str(ROOT), str(self.repo), cwd=self.root)
        shutil.copyfile(SCRIPT, self.repo / 'fitness_logs/automation/monthly_review.py')
        self.git('add', '.')
        self.git('commit', '-qm', 'install monthly runner')
        self.git('init', '--bare', '--quiet', str(self.remote), cwd=self.root)
        self.git('remote', 'set-url', 'origin', str(self.remote))
        self.git('push', '-qu', 'origin', 'main')
        self.env = dict(os.environ, HEALTH_REPO_ROOT=str(self.repo),
                        HEALTH_STATE_ROOT=str(self.root / 'state'),
                        HEALTH_LOG_DIR=str(self.root / 'logs'),
                        HEALTH_LOCK_DIR=str(self.root / 'lock'), HEALTH_GIT_PROXY_URL='')

    def git(self, *args, cwd=None):
        return subprocess.check_output(['git', *args], cwd=cwd or self.repo,
                                       stderr=subprocess.STDOUT, text=True).strip()

    def execute(self):
        return subprocess.run(['python3', str(SCRIPT)], env=self.env, capture_output=True).returncode

    def test_generate_push_and_preserve_on_repeat(self):
        previous = (self.repo / 'fitness_logs/daily/2026-08/2026-08-summary.json').read_bytes()
        self.assertEqual(self.execute(), 0)
        summary = self.repo / 'fitness_logs/daily/2026-09/2026-09-summary.json'
        self.assertTrue(summary.exists())
        self.assertFalse((self.repo / 'fitness_logs/daily/2026-10/2026-10-summary.json').exists())
        head = self.git('rev-parse', 'HEAD')
        self.assertEqual(head, self.git('rev-parse', 'origin/main'))
        self.assertEqual(self.execute(), 0)
        self.assertEqual(head, self.git('rev-parse', 'HEAD'))
        self.assertEqual(previous, (self.repo / 'fitness_logs/daily/2026-08/2026-08-summary.json').read_bytes())
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_failed_push_is_recovered_without_regenerating(self):
        hook = self.remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        self.assertEqual(self.execute(), 1)
        summary = self.repo / 'fitness_logs/daily/2026-09/2026-09-summary.json'
        content = summary.read_bytes()
        head = self.git('rev-parse', 'HEAD')
        self.assertNotEqual(head, self.git('rev-parse', 'origin/main'))
        self.assertEqual(self.git('status', '--porcelain'), '')
        hook.unlink()
        self.assertEqual(self.execute(), 0)
        self.assertEqual(head, self.git('rev-parse', 'origin/main'))
        self.assertEqual(content, summary.read_bytes())

    def test_shared_lock_defers(self):
        lock = self.root / 'lock'
        lock.mkdir()
        (lock / 'pid').write_text(str(os.getpid()))
        self.assertEqual(self.execute(), 75)
        self.assertTrue(lock.exists())

    def test_dirty_checkout_is_preserved(self):
        marker = self.repo / 'user-note.txt'
        marker.write_text('keep me')
        self.assertEqual(self.execute(), 1)
        self.assertEqual(marker.read_text(), 'keep me')
        status = json.loads((self.root / 'state/monthly/latest.json').read_text())
        self.assertEqual(status['status'], 'failed')
        self.assertFalse((self.root / 'lock').exists())

    def test_shanghai_month_boundary(self):
        self.assertIn('2026-09', module.missing_months(self.repo, date(2026, 10, 1)))
        self.assertNotIn('2026-09', module.missing_months(self.repo, date(2026, 9, 30)))
