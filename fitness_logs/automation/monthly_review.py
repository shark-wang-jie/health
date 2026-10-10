#!/usr/bin/env python3
"""Generate missing finished-month summaries using a locked, isolated Git checkout."""
import calendar
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

AUTOMATION_COMMIT = re.compile(r'^fitness: automated (?:review \d{4}-\d{2}-\d{2}|monthly summary \d{4}-\d{2})$')


def missing_months(repo, today):
    result = []
    for folder in sorted((repo / 'fitness_logs/daily').iterdir()):
        if not folder.is_dir() or not re.fullmatch(r'\d{4}-\d{2}', folder.name):
            continue
        year, month = map(int, folder.name.split('-'))
        if today <= datetime(year, month, calendar.monthrange(year, month)[1]).date():
            continue
        if not (folder / f'{folder.name}-summary.json').exists() and any(folder.glob('????-??-??.json')):
            result.append(folder.name)
    return result


def main():
    repo = Path(os.environ.get('HEALTH_REPO_ROOT', '/Users/wangjie/Documents/health')).resolve()
    state = Path(os.environ.get('HEALTH_STATE_ROOT', '/Users/wangjie/Library/Application Support/health-daily-review/state'))
    lock = Path(os.environ.get('HEALTH_LOCK_DIR', '/Users/wangjie/Library/Caches/com.wangjie.health.daily-review.lock'))
    logs = Path(os.environ.get('HEALTH_LOG_DIR', '/Users/wangjie/Library/Logs/health'))
    state.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    status_file = state / 'monthly/latest.json'
    status_file.parent.mkdir(parents=True, exist_ok=True)
    proxy = os.environ.get('HEALTH_GIT_PROXY_URL', 'http://127.0.0.1:15236')
    env = os.environ.copy()
    for key in list(env):
        if key.lower() in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy'):
            del env[key]
    months = []
    owned = False
    attempt = None

    def log(message):
        with (logs / 'monthly.log').open('a') as f:
            f.write(f'[{datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()}] {message}\n')

    def status(kind, code, message):
        temp = status_file.with_suffix(f'.tmp.{os.getpid()}')
        temp.write_text(json.dumps({'status': kind, 'exit_code': code, 'months': months,
                                   'message': message, 'updated_at': datetime.now(timezone.utc).isoformat(),
                                   'attempt': str(attempt) if attempt else None}, ensure_ascii=False, indent=2) + '\n')
        temp.replace(status_file)
        log(message)

    def run(args, cwd=repo):
        process = subprocess.run(args, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=120)
        if process.stdout.strip():
            log(process.stdout.strip())
        if process.returncode:
            raise RuntimeError(f'{args[0:3]} failed ({process.returncode})')
        return process.stdout.strip()

    def git(*args, cwd=repo, network=False):
        command = ['/usr/bin/git']
        if network:
            command += ['-c', f'http.proxy={proxy}']
        command += list(args)
        for retry in range(3 if network else 1):
            try:
                return run(command, cwd)
            except (RuntimeError, subprocess.TimeoutExpired):
                if not network or retry == 2:
                    raise
                time.sleep(5)

    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        try:
            lock.mkdir()
        except FileExistsError:
            # A concurrent owner or an incomplete acquisition is retried later.
            pid_file = lock / 'pid'
            if not pid_file.exists():
                status('deferred', 75, 'shared lock acquisition in progress; retry next interval')
                return 75
            pid = int(pid_file.read_text().strip())
            try:
                os.kill(pid, 0)
                status('deferred', 75, 'daily or monthly task holds shared lock; retry next interval')
                return 75
            except ProcessLookupError:
                stale = lock.with_name(lock.name + f'.monthly-stale.{os.getpid()}')
                lock.rename(stale)
                lock.mkdir()
                shutil.rmtree(stale)
        owned = True
        (lock / 'pid').write_text(str(os.getpid()))
        status('running', 0, 'monthly summary check started')
        if git('rev-parse', '--show-toplevel') != str(repo) or git('branch', '--show-current') != 'main':
            raise RuntimeError('expected repository root on main')
        if git('status', '--porcelain'):
            raise RuntimeError('working tree has pre-existing changes')
        git('fetch', 'origin', network=True)
        git('rebase', 'origin/main')
        subjects = git('log', '--format=%s', 'origin/main..HEAD').splitlines()
        if subjects:
            if not all(AUTOMATION_COMMIT.fullmatch(s) for s in subjects):
                raise RuntimeError('unrecognized local commits; manual review required')
            git('push', 'origin', 'main', network=True)
        base = git('rev-parse', 'HEAD')
        months = missing_months(repo, datetime.now(ZoneInfo('Asia/Shanghai')).date())
        if not months:
            status('success', 0, 'all finished-month summaries already exist; preserved')
            return 0
        runs = state / 'monthly/runs'
        runs.mkdir(parents=True, exist_ok=True)
        attempt = Path(tempfile.mkdtemp(prefix='summary.', dir=runs))
        git('clone', '--quiet', '--no-hardlinks', str(repo), str(attempt))
        git('remote', 'set-url', 'origin', git('remote', 'get-url', 'origin'), cwd=attempt)
        run([sys.executable, 'fitness_logs/build_monthly_summary.py', *months], cwd=attempt)
        expected = {f'fitness_logs/daily/{m}/{m}-summary.json' for m in months}
        for relative in expected:
            run(['/opt/homebrew/bin/jq', 'empty', relative], cwd=attempt)
            payload = json.loads((attempt / relative).read_text())
            if payload['month'] != Path(relative).parent.name:
                raise RuntimeError('summary month mismatch')
        changed = set(git('ls-files', '--others', '--exclude-standard', cwd=attempt).splitlines())
        if changed != expected or git('diff', '--name-only', cwd=attempt):
            raise RuntimeError('generator changed files outside new summaries')
        for month in months:
            relative = f'fitness_logs/daily/{month}/{month}-summary.json'
            git('add', relative, cwd=attempt)
            git('diff', '--cached', '--check', cwd=attempt)
            git('commit', '-m', f'fitness: automated monthly summary {month}', cwd=attempt)
        git('fetch', 'origin', network=True)
        if git('rev-parse', 'origin/main') != base or git('rev-parse', 'HEAD') != base or git('status', '--porcelain'):
            raise RuntimeError('repository changed during generation; isolated output retained')
        git('fetch', str(attempt), 'main')
        git('merge', '--ff-only', 'FETCH_HEAD')
        git('push', 'origin', 'main', network=True)
        shutil.rmtree(attempt)
        attempt = None
        status('success', 0, 'generated and pushed monthly summaries: ' + ', '.join(months))
        return 0
    except Exception as error:
        status('failed', 1, f'{error}; retry next interval; failed workspace retained')
        return 1
    finally:
        if owned:
            shutil.rmtree(lock)


if __name__ == '__main__':
    sys.exit(main())
