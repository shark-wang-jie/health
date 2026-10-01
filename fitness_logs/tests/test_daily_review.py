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
WATCHDOG = ROOT / 'fitness_logs/automation/daily_review_watchdog.sh'
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
        shutil.copyfile(ROOT / 'fitness_logs/automation/daily_repair_prompt.md',
                        self.repo / 'fitness_logs/automation/daily_repair_prompt.md')
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

    def test_bundled_codex_path_is_discovered_after_app_layout_change(self):
        env = dict(self.env)
        env.pop('HEALTH_CODEX_BIN')
        env['HEALTH_CODEX_BUNDLED_BIN'] = str(self.fake)
        result = subprocess.run(['bash', str(SCRIPT)], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        log = (self.root / 'logs' / f'daily-review-{TARGET}.log').read_text()
        self.assertIn(f'Codex CLI: {self.fake}', log)

    def test_nested_codex_binary_is_discovered_dynamically(self):
        env = dict(self.env)
        env.pop('HEALTH_CODEX_BIN')
        env['HEALTH_CODEX_BUNDLED_BIN'] = str(self.root / 'missing-current')
        env['HEALTH_CODEX_LEGACY_BIN'] = str(self.root / 'missing-legacy')
        env['HEALTH_CODEX_SEARCH_ROOT'] = str(self.root)
        result = subprocess.run(['bash', str(SCRIPT)], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        log = (self.root / 'logs' / f'daily-review-{TARGET}.log').read_text()
        self.assertIn(f'Codex CLI: {self.fake}', log)

    def test_deterministic_failure_triggers_restricted_record_repair(self):
        target_path = self.repo / REL
        target = json.loads(target_path.read_text())
        estimated = next(item for item in target['intake_entries']
                         if item['status'] == 'consumed_estimated')
        estimated.pop('uncertainty', None)
        target_path.write_text(json.dumps(target, ensure_ascii=False, indent=2) + '\n')
        self.git('add', REL)
        self.git('commit', '-m', 'break target fixture')
        self.git('push', 'origin', 'main')

        repair_fake = self.root / 'repair-codex'
        repair_fake.write_text(
            '#!/bin/bash\n'
            'workdir=""\n'
            'while [ "$#" -gt 0 ]; do\n'
            '  if [ "$1" = "-C" ]; then workdir="$2"; shift 2; else shift; fi\n'
            'done\n'
            'cat >/dev/null\n'
            f'python3 - "$workdir/{REL}" <<\'PY\'\n'
            'import json, sys\n'
            'from pathlib import Path\n'
            'path=Path(sys.argv[1]); data=json.loads(path.read_text())\n'
            'for item in data["intake_entries"]:\n'
            '    if item.get("status") == "consumed_estimated" and not item.get("uncertainty"):\n'
            '        item["uncertainty"] = "Restored from the existing estimate basis for test repair."\n'
            'path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n")\n'
            'PY\n')
        repair_fake.chmod(0o755)
        self.assertEqual(self.run_review(HEALTH_CODEX_BIN=str(repair_fake)), 0)
        log = (self.root / 'logs' / f'daily-review-{TARGET}.log').read_text()
        self.assertIn('automatic record repair: success', log)
        repaired = json.loads((self.repo / REL).read_text())
        repaired_estimated = next(item for item in repaired['intake_entries']
                                  if item['status'] == 'consumed_estimated')
        self.assertIn('uncertainty', repaired_estimated)


class DailyReviewWatchdogTests(unittest.TestCase):
    def test_repeated_failure_opens_circuit(self):
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp).resolve()
            count_file = root / 'runner-count'
            runner = root / 'runner.sh'
            runner.write_text(f'#!/bin/bash\necho run >> "{count_file}"\nexit 67\n')
            runner.chmod(0o755)
            env = dict(os.environ,
                       HEALTH_REPO_ROOT=str(ROOT),
                       HEALTH_STATE_ROOT=str(root / 'state'),
                       HEALTH_LOG_DIR=str(root / 'logs'),
                       HEALTH_DAILY_REVIEW_RUNNER=str(runner))
            first = subprocess.run(['bash', str(WATCHDOG)], env=env)
            second = subprocess.run(['bash', str(WATCHDOG)], env=env)
            self.assertEqual(first.returncode, 67)
            self.assertEqual(second.returncode, 0)
            self.assertEqual(count_file.read_text().splitlines(), ['run'])
            state = json.loads((root / 'state/watchdog.json').read_text())
            self.assertEqual(state['failure_class'], 'codex_semantic')
            self.assertGreater(state['next_retry_epoch'], 0)


if __name__ == '__main__':
    unittest.main()
