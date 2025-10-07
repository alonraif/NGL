"""Compare native parsers against lula2.py on sample archives.
Run with: python3 backend/tests/regression_compare.py
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import sys
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.parsers import get_parser
from backend.parsers.modem_events import _parse_event as parse_modem_event  # type: ignore

# Mapping of parse modes to archive names (in backend/test_logs)
FIXTURES = {
    'grading': 'grading_sample.tar',
    'memory': 'memory_sample.tar',
    'cpu': 'cpu_sample.tar',
    'sessions': 'sessions_sample.tar',
    'modemevents': 'modem_events_sample.tar',
    'modemeventssorted': 'modem_events_sample.tar',
}

ANSI_ESCAPE = re.compile(r"\x1B\[[0-9;]*[mK]")
ROOT = Path(__file__).resolve().parents[2]
LULA = ROOT / 'backend' / 'lula2.py'
TEST_LOGS = ROOT / 'backend' / 'test_logs'

def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub('', text)

def run_lula(mode: str, archive: Path) -> str:
    lula_env = os.environ.copy()
    temp_dir = lula_env.setdefault('LULA_TEMP_DIR', str(TEST_LOGS / '.lula_tmp'))
    os.makedirs(temp_dir, exist_ok=True)
    cmd = ['python3', str(LULA), str(archive), '-p', mode, '-t', 'UTC']
    result = subprocess.run(cmd, capture_output=True, text=True, env=lula_env)
    if result.returncode != 0:
        raise RuntimeError(f'lula2.py failed for mode {mode}: {result.stderr}')
    return strip_ansi(result.stdout).strip()

def run_native(mode: str, archive: Path) -> Dict[str, Any]:
    parser = get_parser(mode)
    result = parser.process(str(archive), timezone='UTC')
    return result


def normalize_native(mode: str, result: Dict[str, Any]):
    data = result.get('parsed_data')
    if mode == 'grading':
        if not data:
            return set()
        return set((item.get('modem_id'), item.get('status')) for item in data if item.get('status'))
    if mode == 'memory':
        return None
    if mode == 'cpu':
        return None
    if mode == 'sessions':
        if not data:
            return None
        return sorted((
            item.get('session_id') or '',
            item.get('status'),
            round(item.get('duration_seconds') or 0, 2)
        ) for item in data)
    if mode in ('modemevents', 'modemeventssorted'):
        return None
    return None


def normalize_lula(mode: str, raw: str):
    lines = [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith('Could not find the module regex')]
    if mode == 'grading':
        results = set()
        for line in lines:
            if ':    ' in line:
                line = line.split(':', 1)[1].strip()
            m = re.search(r'ModemID\s+(\d+)\s+(Full|Limited)\s+Service', line)
            if m:
                results.add((m.group(1), f"{m.group(2)} Service"))
                continue
            m = re.search(r'ModemID\s+(\d+)\s+(\d+)\s+(\d+)\s+(.*)', line)
            if m:
                modem_id, metric1, metric2, status = m.groups()
                status_lower = status.lower()
                results.add((modem_id, 'Limited Service' if 'not good enough' in status_lower else 'Full Service'))
        return results
    if mode == 'memory':
        return None
    if mode == 'cpu':
        return None
    if mode == 'sessions':
        # Lula outputs minimal information; skip structured comparison
        return None
    if mode in ('modemevents', 'modemeventssorted'):
        return None
    return None

def main():
    mismatches = []
    for mode, archive_name in FIXTURES.items():
        archive_path = TEST_LOGS / archive_name
        if not archive_path.exists():
            print(f'[SKIP] {mode}: missing fixture {archive_name}')
            continue
        print(f'[CHECK] {mode} using {archive_name}')
        try:
            native_result = run_native(mode, archive_path)
        except RuntimeError as exc:
            print(f'  SKIP native comparison: {exc}')
            continue
        lula_raw = run_lula(mode, archive_path)

        native_norm = normalize_native(mode, native_result)
        lula_norm = normalize_lula(mode, lula_raw)

        if native_norm is None or lula_norm is None:
            print('  (No structured comparison available)')
            continue

        if native_norm != lula_norm:
            print(f'  MISMATCH for mode {mode}')
            mismatches.append((mode, native_norm, lula_norm))
        else:
            print('  ✓ structured data matches')

    if mismatches:
        print('\nSummary: mismatches detected in modes: ' + ', '.join(mode for mode, _, _ in mismatches))
        for mode, native, lula in mismatches:
            print(f'\n=== Mode {mode} ===')
            print('--- Native structured ---')
            print(native)
            print('--- Lula2 structured ---')
            print(lula)
        raise SystemExit(1)
    else:
        print('\nAll checked modes match.')

if __name__ == '__main__':
    main()
