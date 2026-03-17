"""
Log Parser - Parse Android logcat logs into structured format
"""

import re
from datetime import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class LogEntry:
    """Represents a single logcat entry"""
    timestamp: str
    level: str
    tag: str
    pid: int
    message: str
    raw: str


LOGCAT_PATTERN = re.compile(
    r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+'  # timestamp
    r'([VDIWEF])/'                                  # level
    r'([^\(\s]+)'                                   # tag
    r'\(\s*(\d+)\)'                                 # PID
    r':\s*(.*)$'                                    # message
)


def parse_line(line: str) -> Optional[LogEntry]:
    """Parse a single logcat line into LogEntry"""
    match = LOGCAT_PATTERN.match(line.strip())
    if not match:
        return None

    return LogEntry(
        timestamp=match.group(1),
        level=match.group(2),
        tag=match.group(3),
        pid=int(match.group(4)),
        message=match.group(5),
        raw=line
    )


def parse_file(filepath: str) -> list[LogEntry]:
    """Parse entire log file"""
    entries = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            entry = parse_line(line)
            if entry:
                entries.append(entry)
    return entries


def filter_by_level(entries: list[LogEntry], levels: str) -> list[LogEntry]:
    """Filter entries by log level (e.g., 'EW' for Error and Warning)"""
    return [e for e in entries if e.level in levels]


def filter_by_tag(entries: list[LogEntry], tag_pattern: str) -> list[LogEntry]:
    """Filter entries by tag regex pattern"""
    pattern = re.compile(tag_pattern, re.IGNORECASE)
    return [e for e in entries if pattern.search(e.tag)]


def filter_by_pid(entries: list[LogEntry], pid: int) -> list[LogEntry]:
    """Filter entries by process ID"""
    return [e for e in entries if e.pid == pid]


if __name__ == '__main__':
    # Example usage
    import sys
    if len(sys.argv) < 2:
        print("Usage: python log_parser.py <logfile>")
        sys.exit(1)

    entries = parse_file(sys.argv[1])
    print(f"Parsed {len(entries)} entries")

    # Show errors
    errors = filter_by_level(entries, 'EF')
    print(f"\nErrors/Fatals: {len(errors)}")
    for e in errors[:10]:
        print(f"  [{e.level}] {e.tag}: {e.message[:80]}")