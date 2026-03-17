"""
Log Parser - Parse Android logcat logs into structured format

支持多种日志格式:
- Android TV logcat: MM-DD HH:MM:SS.mmm Level/Tag(PID): Message
- Android STB ROM logcat: MM-DD HH:MM:SS.mmm PID TID Level Tag: Message
"""

import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum


class PlatformType(Enum):
    """平台类型枚举"""
    ANDROID_TV = "android_tv"           # Android TV + homed APK (原格式)
    ANDROID_STB_ROM = "android_stb_rom" # Android 机顶盒 ROM + homed APK
    LINUX_STB = "linux_stb"             # Linux 机顶盒
    UNKNOWN = "unknown"


@dataclass
class LogEntry:
    """Represents a single log entry"""
    timestamp: str
    level: str
    tag: str
    pid: int
    message: str
    raw: str
    tid: Optional[int] = None                    # 线程ID (Android STB ROM)
    platform: PlatformType = PlatformType.UNKNOWN


# Android TV logcat 格式: MM-DD HH:MM:SS.mmm Level/Tag(PID): Message
# 示例: 03-09 16:00:46.289 D/aml_hal_core_detect( 395): Message
LOGCAT_ANDROID_TV_PATTERN = re.compile(
    r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+'  # timestamp
    r'([VDIWEF])/'                                  # level
    r'([^\(\s]+)'                                   # tag
    r'\(\s*(\d+)\)'                                 # PID
    r':\s*(.*)$'                                    # message
)

# Android STB ROM logcat 格式: MM-DD HH:MM:SS.mmm PID TID Level Tag: Message
# 示例: 01-01 08:00:00.312  2069  2069 W auditd  : type=2000 audit...
LOGCAT_ANDROID_STB_ROM_PATTERN = re.compile(
    r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+'  # timestamp
    r'(\d+)\s+'                                     # PID
    r'(\d+)\s+'                                     # TID
    r'([VDIWEF])\s+'                                # level
    r'([^\s:]+)\s*'                                 # tag
    r':\s*(.*)$'                                    # message
)

# Linux STB 自定义格式 (可选支持)
# 示例: [I][93][porting_display_init:78](in)
LINUX_STB_PATTERN = re.compile(
    r'^\[([VDIWEF])\]'                              # level
    r'\[tm:(\d+)\]'                                 # timestamp (毫秒)
    r'\[tid:([0-9a-fA-F]+)\]'                       # thread id (hex)
    r'\s*(.*)$'                                     # message
)


def detect_platform(line: str) -> PlatformType:
    """
    检测日志行所属平台类型

    Returns:
        PlatformType: 检测到的平台类型
    """
    line = line.strip()

    # 跳过 logcat 的分隔行
    if line.startswith('--------- beginning of'):
        return PlatformType.UNKNOWN

    # 优先检测 Android STB ROM 格式 (带 TID)
    if LOGCAT_ANDROID_STB_ROM_PATTERN.match(line):
        return PlatformType.ANDROID_STB_ROM

    # 检测 Android TV 格式
    if LOGCAT_ANDROID_TV_PATTERN.match(line):
        return PlatformType.ANDROID_TV

    # 检测 Linux STB 格式
    if LINUX_STB_PATTERN.match(line):
        return PlatformType.LINUX_STB

    return PlatformType.UNKNOWN


def parse_line(line: str, platform_hint: PlatformType = None) -> Optional[LogEntry]:
    """
    Parse a single log line into LogEntry

    Args:
        line: 日志行
        platform_hint: 可选的平台提示，用于加速解析

    Returns:
        LogEntry 或 None
    """
    line_stripped = line.strip()

    # 跳过分隔行
    if line_stripped.startswith('--------- beginning of'):
        return None

    # 如果有平台提示，优先尝试对应格式
    if platform_hint == PlatformType.ANDROID_STB_ROM:
        match = LOGCAT_ANDROID_STB_ROM_PATTERN.match(line_stripped)
        if match:
            return LogEntry(
                timestamp=match.group(1),
                pid=int(match.group(2)),
                tid=int(match.group(3)),
                level=match.group(4),
                tag=match.group(5),
                message=match.group(6),
                raw=line,
                platform=PlatformType.ANDROID_STB_ROM
            )
    elif platform_hint == PlatformType.ANDROID_TV:
        match = LOGCAT_ANDROID_TV_PATTERN.match(line_stripped)
        if match:
            return LogEntry(
                timestamp=match.group(1),
                level=match.group(2),
                tag=match.group(3),
                pid=int(match.group(4)),
                message=match.group(5),
                raw=line,
                platform=PlatformType.ANDROID_TV
            )

    # 自动检测格式
    # 1. 尝试 Android STB ROM 格式
    match = LOGCAT_ANDROID_STB_ROM_PATTERN.match(line_stripped)
    if match:
        return LogEntry(
            timestamp=match.group(1),
            pid=int(match.group(2)),
            tid=int(match.group(3)),
            level=match.group(4),
            tag=match.group(5),
            message=match.group(6),
            raw=line,
            platform=PlatformType.ANDROID_STB_ROM
        )

    # 2. 尝试 Android TV 格式
    match = LOGCAT_ANDROID_TV_PATTERN.match(line_stripped)
    if match:
        return LogEntry(
            timestamp=match.group(1),
            level=match.group(2),
            tag=match.group(3),
            pid=int(match.group(4)),
            message=match.group(5),
            raw=line,
            platform=PlatformType.ANDROID_TV
        )

    # 3. 尝试 Linux STB 格式
    match = LINUX_STB_PATTERN.match(line_stripped)
    if match:
        return LogEntry(
            timestamp=match.group(2),  # tm in ms
            level=match.group(1),
            tag="",
            pid=0,
            tid=int(match.group(3), 16),  # hex tid
            message=match.group(4),
            raw=line,
            platform=PlatformType.LINUX_STB
        )

    return None


def detect_file_platform(filepath: str, sample_lines: int = 100) -> PlatformType:
    """
    检测日志文件的主要平台类型

    Args:
        filepath: 日志文件路径
        sample_lines: 采样行数

    Returns:
        检测到的主要平台类型
    """
    counts = {pt: 0 for pt in PlatformType}

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i >= sample_lines:
                break
            platform = detect_platform(line)
            counts[platform] += 1

    # 找出最多的平台类型（排除 UNKNOWN）
    counts.pop(PlatformType.UNKNOWN)
    if not counts or max(counts.values()) == 0:
        return PlatformType.UNKNOWN

    return max(counts, key=counts.get)


def parse_file(filepath: str, auto_detect: bool = True) -> list[LogEntry]:
    """
    Parse entire log file

    Args:
        filepath: 日志文件路径
        auto_detect: 是否自动检测平台类型

    Returns:
        解析后的日志条目列表
    """
    entries = []
    platform_hint = None

    if auto_detect:
        platform_hint = detect_file_platform(filepath)

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            entry = parse_line(line, platform_hint)
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


def filter_by_tid(entries: list[LogEntry], tid: int) -> list[LogEntry]:
    """Filter entries by thread ID (Android STB ROM)"""
    return [e for e in entries if e.tid == tid]


def filter_by_platform(entries: list[LogEntry], platform: PlatformType) -> list[LogEntry]:
    """Filter entries by platform type"""
    return [e for e in entries if e.platform == platform]


def get_platform_stats(entries: list[LogEntry]) -> dict[PlatformType, int]:
    """获取各平台类型的统计"""
    stats = {}
    for e in entries:
        stats[e.platform] = stats.get(e.platform, 0) + 1
    return stats


if __name__ == '__main__':
    # Example usage
    import sys
    if len(sys.argv) < 2:
        print("Usage: python log_parser.py <logfile>")
        print("\n支持的平台格式:")
        print("  - Android TV logcat:     MM-DD HH:MM:SS.mmm Level/Tag(PID): Message")
        print("  - Android STB ROM logcat: MM-DD HH:MM:SS.mmm PID TID Level Tag: Message")
        print("  - Linux STB:             [Level][tm:X][tid:XXX] Message")
        sys.exit(1)

    filepath = sys.argv[1]
    entries = parse_file(filepath)

    print(f"Parsed {len(entries)} entries")

    # 显示平台统计
    stats = get_platform_stats(entries)
    print(f"\n平台分布:")
    for platform, count in stats.items():
        print(f"  {platform.value}: {count} entries")

    # Show errors
    errors = filter_by_level(entries, 'EF')
    print(f"\nErrors/Fatals: {len(errors)}")
    for e in errors[:10]:
        tid_str = f" TID:{e.tid}" if e.tid else ""
        print(f"  [{e.level}] {e.tag} (PID:{e.pid}{tid_str}): {e.message[:80]}")