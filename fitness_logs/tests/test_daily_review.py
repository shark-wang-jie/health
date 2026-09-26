"""Run the real scheduler against local Git remotes and a fake AI process."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'fitness_logs/automation/daily_review.sh'
TARGET = '2026-09-21'
REL = f'fitness_logs/daily/2026-09/{TARGET}.json'


class DailyReviewRecoveryTests(unittest.TestCase):
    def git(self, *args, cwd=None):
        return subprocess.check_output(['git', *args], cwd=cwd or self.repo,
                                       stderr=subprocess.STDOUT, text=True).strip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / 'repo'
        self.remote = self.root / 'remote.git'
        self.git('clone', '--quiet', '--no-hardlinks', str(ROOT), str(self.repo), cwd=self.root)
        shutil.copyfile(SCRIPT, self.repo / 'fitness_logs/automation/daily_review.sh')
        target_path = self.repo / REL
        target = json.loads(target_path.read_text())
        target['daily_summary']['warnings'] = ['stale test fixture']
        target_path.write_text(json.dumps(target, ensure_ascii=False, indent=2) + '\n')
        self.git('config', 'user.name', 'Scheduler test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('add', '.')
        self.git('commit', '--allow-empty', '-m', 'test fixture')
        self.git('init', '--bare', str(self.remote), cwd=self.root)
        self.git('remote', 'set-url', 'origin', str(self.remote))
        self.git('push', '-u', 'origin', 'main')
        self.fake = self.root / 'codex'
        self.fake.write_text('#!/bin/bash\ncat >/dev/null\nexit "${FAKE_AI_EXIT:-0}"\n')
        self.fake.chmod(0o755)
        self.state = self.root / 'state'
        self.env = dict(os.environ, HEALTH_REPO_ROOT=str(self.repo),
                        HEALTH_STATE_ROOT=str(self.state),
                        HEALTH_LOG_DIR=str(self.root / 'logs'),
                        HEALTH_LOCK_DIR=str(self.root / 'lock'),
                        HEALTH_CODEX_BIN=str(self.fake), HEALTH_TARGET_DATE=TARGET,
                        HEALTH_NETWORK_ATTEMPTS='1')

    def run_review(self, **env):
        return subprocess.run(['bash', str(SCRIPT)], env=dict(self.env, **env),
                              capture_output=True, text=True).returncode

    def test_quota_failure_leaves_clean_checkout_and_retry_succeeds(self):
        before = (self.repo / REL).read_bytes()
        self.assertEqual(self.run_review(FAKE_AI_EXIT='1'), 67)
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertEqual((self.repo / REL).read_bytes(), before)
        attempts = list((self.state / 'runs').iterdir())
        self.assertEqual(len(attempts), 1)
        self.assertNotEqual((attempts[0] / REL).read_bytes(), before)
        self.assertTrue((self.state / 'pending' / f'{TARGET}.pending').exists())
        self.assertEqual(self.run_review(), 0)
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertTrue((self.state / 'completed' / f'{TARGET}.sha256').exists())
        self.assertFalse((self.state / 'pending' / f'{TARGET}.pending').exists())
        self.assertEqual(len(list((self.state / 'runs').iterdir())), 1)

    def test_external_dirty_checkout_is_preserved(self):
        path = self.repo / 'README.md'
        path.write_text('external work\n')
        self.assertEqual(self.run_review(), 65)
        self.assertEqual(path.read_text(), 'external work\n')

    def test_failed_push_retains_commit_and_recovers(self):
        hook = self.remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        self.assertEqual(self.run_review(), 74)
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertEqual(self.git('rev-list', '--count', 'origin/main..HEAD'), '1')
        hook.unlink()
        self.assertEqual(self.run_review(), 0)
        self.assertEqual(self.git('rev-list', '--count', 'origin/main..HEAD'), '0')

    def test_backlog_days_are_queued_even_while_oldest_fails(self):
        pending = self.state / 'pending'
        pending.mkdir(parents=True)
        (pending / '2026-09-21.pending').touch()
        self.assertEqual(self.run_review(FAKE_AI_EXIT='1'), 67)
        self.assertTrue((pending / '2026-09-22.pending').exists())
        self.assertTrue((pending / '2026-09-23.pending').exists())
        self.assertTrue((pending / '2026-09-24.pending').exists())


if __name__ == '__main__':
    unittest.main()
