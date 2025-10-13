"""
Docker service helper for fetching container logs
"""
import subprocess
import re
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple


# Valid Docker Compose services
VALID_SERVICES = [
    'backend',
    'frontend',
    'postgres',
    'redis',
    'celery_worker',
    'celery_beat',
    'certbot'
]


class DockerServiceError(Exception):
    """Exception raised for Docker service errors"""
    pass


def is_docker_available() -> bool:
    """Check if Docker and docker-compose are available"""
    try:
        # Check docker-compose
        result = subprocess.run(
            ['docker-compose', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_available_services() -> List[str]:
    """
    Get list of available Docker services from docker-compose

    Returns:
        List of service names
    """
    try:
        # Use mounted docker-compose.yml file
        compose_file = '/docker-compose.yml'
        project_name = 'ngl'  # Match the project name

        # Get list of services from docker-compose
        result = subprocess.run(
            ['docker-compose', '-f', compose_file, '-p', project_name, 'ps', '--services'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise DockerServiceError(f"Failed to get services: {result.stderr}")

        services = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
        return services

    except subprocess.TimeoutExpired:
        raise DockerServiceError("Docker command timed out")
    except FileNotFoundError:
        raise DockerServiceError("docker-compose not found")
    except Exception as e:
        raise DockerServiceError(f"Failed to get services: {str(e)}")


def parse_docker_log_line(line: str) -> Optional[Dict[str, str]]:
    """
    Parse a single Docker log line with timestamp and service name

    Format: service_name | timestamp | message

    Args:
        line: Raw log line

    Returns:
        Dict with timestamp, service, and message, or None if parsing fails
    """
    if not line.strip():
        return None

    # Match format: service_name | 2025-01-13T10:30:45.123456789Z message
    # Docker logs format with --timestamps: "service | timestamp message"
    match = re.match(r'^(\S+)\s+\|\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+(.*)$', line)

    if match:
        service, timestamp_str, message = match.groups()
        return {
            'service': service,
            'timestamp': timestamp_str,
            'message': message.strip()
        }

    # Fallback for lines without proper format
    return {
        'service': 'unknown',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'message': line.strip()
    }


def get_docker_logs(
    service: str = 'all',
    since: str = '1h',
    tail: int = 500
) -> Tuple[List[Dict[str, str]], int]:
    """
    Get Docker logs for specified service(s)

    Args:
        service: Service name or 'all' for all services
        since: Time duration (e.g., '1h', '2h', '24h', '30m')
        tail: Number of lines to retrieve (max 2000)

    Returns:
        Tuple of (parsed logs, total_lines)

    Raises:
        DockerServiceError: If Docker is not available or command fails
    """
    if not is_docker_available():
        raise DockerServiceError("Docker is not available")

    # Validate service
    if service != 'all' and service not in VALID_SERVICES:
        raise DockerServiceError(f"Invalid service: {service}. Valid services: {', '.join(VALID_SERVICES)}")

    # Limit tail to prevent memory issues
    tail = min(int(tail), 2000)

    # Use mounted docker-compose.yml file
    compose_file = '/docker-compose.yml'
    project_name = 'ngl'

    # Build command
    cmd = [
        'docker-compose',
        '-f', compose_file,
        '-p', project_name,
        'logs',
        '--tail', str(tail),
        '--since', since,
        '--timestamps',
        '--no-color'
    ]

    # Add service filter if not 'all'
    if service != 'all':
        cmd.append(service)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise DockerServiceError(f"Docker command failed: {result.stderr}")

        # Parse logs
        raw_logs = result.stdout
        lines = raw_logs.split('\n')

        parsed_logs = []
        for line in lines:
            parsed = parse_docker_log_line(line)
            if parsed:
                parsed_logs.append(parsed)

        return parsed_logs, len(parsed_logs)

    except subprocess.TimeoutExpired:
        raise DockerServiceError("Docker command timed out (30s limit)")
    except Exception as e:
        raise DockerServiceError(f"Failed to get logs: {str(e)}")


def get_service_status() -> Dict[str, Dict[str, str]]:
    """
    Get status of all Docker services

    Returns:
        Dict with service names as keys and status info as values
    """
    try:
        # Use mounted docker-compose.yml file
        compose_file = '/docker-compose.yml'
        project_name = 'ngl'

        # Get service status
        result = subprocess.run(
            ['docker-compose', '-f', compose_file, '-p', project_name, 'ps', '--format', 'json'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return {}

        # Parse JSON output (docker-compose ps --format json gives one JSON per line)
        import json
        services = {}

        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                service_name = data.get('Service', data.get('Name', 'unknown'))
                services[service_name] = {
                    'status': data.get('State', data.get('Status', 'unknown')),
                    'health': data.get('Health', ''),
                    'name': data.get('Name', ''),
                }
            except json.JSONDecodeError:
                continue

        return services

    except Exception:
        return {}


def validate_time_range(since: str) -> bool:
    """
    Validate time range format

    Args:
        since: Time range string (e.g., '1h', '2h', '24h', '30m')

    Returns:
        True if valid, False otherwise
    """
    # Docker accepts formats like: 1h, 2h, 30m, 1d, etc.
    return bool(re.match(r'^\d+[smhd]$', since))
