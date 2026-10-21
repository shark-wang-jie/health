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
        # Keep a missing finished month regardless of summaries already in ROOT.
        (self.repo / 'fitness_logs/daily/2026-09/2026-09-summary.json').unlink(missing_ok=True)
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

    def conflicting_commits(self, subject):
        relative = 'fitness_logs/sync-fixture.txt'
        (self.repo / relative).write_text('base\n')
        self.git('add', relative)
        self.git('commit', '-qm', 'shared conflict fixture')
        self.git('push', '-q', 'origin', 'main')
        peer = self.root / 'peer'
        self.git('clone', '--quiet', str(self.remote), str(peer), cwd=self.root)
        (self.repo / relative).write_text('local automated work\n')
        self.git('add', relative)
        self.git('commit', '-qm', subject)
        original_head = self.git('rev-parse', 'HEAD')
        (peer / relative).write_text('remote user update\n')
        self.git('add', relative, cwd=peer)
        self.git('commit', '-qm', 'remote user update', cwd=peer)
        self.git('push', '-q', 'origin', 'main', cwd=peer)
        return original_head

    def assert_original_checkout(self, original_head):
        self.assertEqual(self.git('branch', '--show-current'), 'main')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertEqual(self.git('rev-parse', 'HEAD'), original_head)
        self.assertFalse((self.repo / '.git/rebase-merge').exists())
        self.assertFalse((self.repo / '.git/rebase-apply').exists())
        self.assertEqual((self.repo / 'fitness_logs/sync-fixture.txt').read_text(),
                         'local automated work\n')

    def test_sync_conflict_aborts_and_preserves_automation_commit(self):
        subject = 'fitness: automated monthly summary 2026-09'
        original_head = self.conflicting_commits(subject)
        self.assertEqual(self.execute(), 1)
        self.assert_original_checkout(original_head)
        self.assertEqual(self.git('log', '--format=%s', 'origin/main..HEAD'), subject)
        evidence = list((self.root / 'state/git-sync').iterdir())
        self.assertEqual(len(evidence), 1)
        self.assertEqual((evidence[0] / 'original-head.txt').read_text().strip(), original_head)
        self.assertIn('UU fitness_logs/sync-fixture.txt', (evidence[0] / 'status.txt').read_text())
        self.assertIn('local automated work', (evidence[0] / 'current-commit.patch').read_text())

    def test_unrecognized_local_commit_is_rejected_before_rebase(self):
        original_head = self.conflicting_commits('user work must stay untouched')
        self.assertEqual(self.execute(), 1)
        self.assert_original_checkout(original_head)
        self.assertFalse((self.root / 'state/git-sync').exists())
        status = json.loads((self.root / 'state/monthly/latest.json').read_text())
        self.assertIn('unrecognized local commits', status['message'])

    def test_existing_rebase_is_left_untouched(self):
        self.conflicting_commits('fitness: automated monthly summary 2026-09')
        self.git('fetch', 'origin')
        result = subprocess.run(['git', 'rebase', 'origin/main'], cwd=self.repo,
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        before_status = self.git('status', '--porcelain')
        before_head = self.git('rev-parse', 'HEAD')
        self.assertEqual(self.execute(), 1)
        self.assertEqual(self.git('status', '--porcelain'), before_status)
        self.assertEqual(self.git('rev-parse', 'HEAD'), before_head)
        self.assertTrue((self.repo / '.git/rebase-merge').exists())
        self.assertFalse((self.root / 'state/git-sync').exists())

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
