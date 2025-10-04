#!/usr/bin/env python3
"""
Automated Parser Testing Script
Tests all 12 parser modes with a sample log file and verifies results
"""
import requests
import json
import time
import os
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:5000"
CONFIG_FILE = "/app/test_config.json"  # Absolute path in Docker container

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# All parser modes to test
PARSER_MODES = [
    {'value': 'known', 'label': 'Known Errors'},
    {'value': 'error', 'label': 'All Errors'},
    {'value': 'v', 'label': 'Verbose Errors'},
    {'value': 'all', 'label': 'All Lines'},
    {'value': 'bw', 'label': 'Bandwidth'},
    {'value': 'md-bw', 'label': 'Modem Bandwidth'},
    {'value': 'md-db-bw', 'label': 'Data Bridge Bandwidth'},
    {'value': 'md', 'label': 'Modem Statistics'},
    {'value': 'sessions', 'label': 'Sessions'},
    {'value': 'id', 'label': 'Device IDs'},
    {'value': 'memory', 'label': 'Memory Usage'},
    {'value': 'grading', 'label': 'Modem Grading'},
]


def load_config():
    """Load test configuration"""
    config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        print(f"{RED}Error: {CONFIG_FILE} not found{RESET}")
        print(f"Expected at: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    # Validate required fields
    if config.get('begin_date') == 'REPLACE_WITH_YOUR_START_DATE':
        print(f"{RED}Error: Please update begin_date in {CONFIG_FILE}{RESET}")
        sys.exit(1)

    if config.get('end_date') == 'REPLACE_WITH_YOUR_END_DATE':
        print(f"{RED}Error: Please update end_date in {CONFIG_FILE}{RESET}")
        sys.exit(1)

    # Check test file exists (resolve from /app root in container)
    test_file_path = Path('/app') / config['test_file']
    if not test_file_path.exists():
        print(f"{RED}Error: Test file not found: {test_file_path}{RESET}")
        print(f"Please place your test log file at: {test_file_path}")
        sys.exit(1)

    config['test_file_path'] = str(test_file_path)
    return config


def login(config):
    """Login and get JWT token"""
    print(f"\n{BLUE}Logging in as {config['test_user']['username']}...{RESET}")

    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                'username': config['test_user']['username'],
                'password': config['test_user']['password']
            }
        )

        if response.status_code == 200:
            data = response.json()
            # Support both 'token' and 'access_token' response formats
            token = data.get('token') or data.get('access_token')
            if not token:
                print(f"{RED}✗ Login response missing token. Response: {data}{RESET}")
                sys.exit(1)
            print(f"{GREEN}✓ Login successful{RESET}")
            return token
        elif response.status_code == 401:
            # Try to create user if login fails
            print(f"{YELLOW}User not found, attempting to create test user...{RESET}")
            return create_user_and_login(config)
        else:
            print(f"{RED}✗ Login failed: {response.status_code} {response.text}{RESET}")
            sys.exit(1)
    except Exception as e:
        print(f"{RED}✗ Login error: {e}{RESET}")
        print(f"{YELLOW}Make sure the backend is running on {BASE_URL}{RESET}")
        sys.exit(1)


def create_user_and_login(config):
    """Create test user and login (requires admin or public registration)"""
    print(f"{BLUE}Creating test user...{RESET}")

    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            'username': config['test_user']['username'],
            'password': config['test_user']['password'],
            'email': config['test_user']['email']
        }
    )

    if response.status_code == 201:
        print(f"{GREEN}✓ User created successfully{RESET}")
        return login(config)
    else:
        print(f"{RED}✗ Failed to create user: {response.status_code} {response.text}{RESET}")
        print(f"{YELLOW}Note: You may need to manually create the test user as admin{RESET}")
        sys.exit(1)


def upload_and_parse(token, config, parse_mode, mode_label):
    """Upload file and trigger parsing for a specific mode"""
    headers = {'Authorization': f'Bearer {token}'}

    # Prepare form data
    with open(config['test_file_path'], 'rb') as f:
        files = {'file': (os.path.basename(config['test_file_path']), f)}
        data = {
            'parse_mode': parse_mode,
            'session_name': f"{config['session_name_prefix']} - {mode_label}",
            'zendesk_case': config['zendesk_case'],
            'timezone': config['timezone'],
            'begin_date': config['begin_date'],
            'end_date': config['end_date']
        }

        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/upload",
            headers=headers,
            files=files,
            data=data
        )

    if response.status_code == 200:
        result = response.json()
        duration = time.time() - start_time
        return {
            'success': True,
            'analysis_id': result.get('analysis_id'),
            'duration': duration,
            'result': result
        }
    else:
        duration = time.time() - start_time
        return {
            'success': False,
            'error': response.text,
            'status_code': response.status_code,
            'duration': duration
        }


def wait_for_completion(token, analysis_id, config):
    """Poll analysis status until completion or timeout"""
    headers = {'Authorization': f'Bearer {token}'}
    timeout = config['timeout_seconds']
    poll_interval = config['poll_interval_seconds']
    start_time = time.time()

    while time.time() - start_time < timeout:
        response = requests.get(
            f"{BASE_URL}/api/analyses/{analysis_id}",
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            # The response has 'analysis' nested inside
            analysis = data.get('analysis', {})
            status = analysis.get('status')

            if status == 'completed':
                return {'success': True, 'analysis': data}
            elif status == 'failed':
                return {'success': False, 'error': analysis.get('error_message', 'Unknown error')}

        time.sleep(poll_interval)

    return {'success': False, 'error': 'Timeout waiting for completion'}


def run_test(token, config, mode_info):
    """Run test for a single parser mode"""
    parse_mode = mode_info['value']
    mode_label = mode_info['label']

    print(f"\n{BLUE}Testing: {mode_label} ({parse_mode}){RESET}")
    print(f"  Uploading and parsing...")

    # Upload and parse
    result = upload_and_parse(token, config, parse_mode, mode_label)

    if not result['success']:
        print(f"  {RED}✗ Upload failed: {result.get('error', 'Unknown error')}{RESET}")
        return {
            'mode': parse_mode,
            'label': mode_label,
            'success': False,
            'error': result.get('error'),
            'duration': result.get('duration', 0)
        }

    print(f"  {GREEN}✓ Upload successful ({result['duration']:.2f}s){RESET}")
    analysis_id = result.get('analysis_id')

    if not analysis_id:
        # Synchronous processing - already complete
        return {
            'mode': parse_mode,
            'label': mode_label,
            'success': True,
            'analysis_id': None,
            'duration': result['duration'],
            'result': result['result']
        }

    # Wait for async completion
    print(f"  Waiting for completion (analysis_id: {analysis_id})...")
    completion_result = wait_for_completion(token, analysis_id, config)

    if completion_result['success']:
        total_duration = time.time() - (time.time() - result['duration'])
        print(f"  {GREEN}✓ Completed successfully ({total_duration:.2f}s total){RESET}")
        return {
            'mode': parse_mode,
            'label': mode_label,
            'success': True,
            'analysis_id': analysis_id,
            'duration': total_duration,
            'result': completion_result['analysis']
        }
    else:
        print(f"  {RED}✗ Failed: {completion_result['error']}{RESET}")
        return {
            'mode': parse_mode,
            'label': mode_label,
            'success': False,
            'analysis_id': analysis_id,
            'error': completion_result['error'],
            'duration': result['duration']
        }


def print_summary(results):
    """Print test summary"""
    print(f"\n{'='*70}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{'='*70}")

    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed

    print(f"\nResults: {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET} out of {len(results)} total\n")

    # Detailed results table
    print(f"{'Mode':<15} {'Label':<25} {'Status':<10} {'Duration':<10} {'Analysis ID'}")
    print(f"{'-'*70}")

    for r in results:
        status = f"{GREEN}✓ PASS{RESET}" if r['success'] else f"{RED}✗ FAIL{RESET}"
        duration = f"{r['duration']:.2f}s"
        analysis_id = str(r.get('analysis_id', 'N/A'))
        print(f"{r['mode']:<15} {r['label']:<25} {status:<20} {duration:<10} {analysis_id}")

    # Failed tests details
    if failed > 0:
        print(f"\n{RED}Failed Tests Details:{RESET}")
        for r in results:
            if not r['success']:
                print(f"  • {r['label']} ({r['mode']}): {r.get('error', 'Unknown error')}")

    print(f"\n{'='*70}")
    print(f"{GREEN if failed == 0 else YELLOW}All tests can be viewed in the History tab{RESET}")
    print(f"{'='*70}\n")


def main():
    """Main test execution"""
    print(f"\n{'='*70}")
    print(f"{BLUE}NGL AUTOMATED PARSER TESTING{RESET}")
    print(f"{'='*70}")

    # Load configuration
    config = load_config()
    print(f"\n{BLUE}Configuration:{RESET}")
    print(f"  Test file: {config['test_file_path']}")
    print(f"  Date range: {config['begin_date']} to {config['end_date']}")
    print(f"  Timezone: {config['timezone']}")
    print(f"  Timeout: {config['timeout_seconds']}s")

    # Login
    token = login(config)

    # Run tests for all parser modes
    results = []
    start_time = time.time()

    for mode_info in PARSER_MODES:
        result = run_test(token, config, mode_info)
        results.append(result)

    total_duration = time.time() - start_time

    # Print summary
    print_summary(results)

    print(f"Total execution time: {total_duration:.2f}s")

    # Exit with appropriate code
    failed_count = sum(1 for r in results if not r['success'])
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == '__main__':
    main()
