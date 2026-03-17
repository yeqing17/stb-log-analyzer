"""
Pattern Matcher - Match known error patterns in logcat logs

支持平台:
- Android TV logcat
- Android STB ROM logcat
- Linux STB

Usage:
    python pattern_matcher.py <logfile>
    python pattern_matcher.py <logfile> --module cbn
    python pattern_matcher.py <logfile> --severity error
    python pattern_matcher.py <logfile> --platform android_stb_rom
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class PlatformType(Enum):
    """平台类型枚举"""
    ANDROID_TV = "android_tv"
    ANDROID_STB_ROM = "android_stb_rom"
    LINUX_STB = "linux_stb"
    UNKNOWN = "unknown"


@dataclass
class Pattern:
    """Represents an error pattern"""
    name: str
    regex: str
    severity: str
    description: str
    module: Optional[str] = None
    platforms: Optional[List[PlatformType]] = None  # 适用平台，None表示所有平台


@dataclass
class Match:
    """Represents a pattern match"""
    pattern: Pattern
    line_number: int
    line_content: str
    matched_text: str
    platform: PlatformType = PlatformType.UNKNOWN


def load_config(config_path: str = None) -> dict:
    """Load keywords configuration from YAML file"""
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "keywords.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_platforms(platform_list: list) -> List[PlatformType]:
    """解析平台列表字符串为PlatformType枚举"""
    if not platform_list:
        return None  # None表示所有平台
    result = []
    for p in platform_list:
        try:
            result.append(PlatformType(p.lower()))
        except ValueError:
            pass
    return result if result else None


def build_patterns_from_config(config: dict) -> list[Pattern]:
    """Build Pattern objects from YAML config"""
    patterns = []

    for module_name, module_data in config.items():
        if module_name == 'cases':
            continue  # Skip case index

        if isinstance(module_data, dict) and 'patterns' in module_data:
            for p in module_data['patterns']:
                platforms = parse_platforms(p.get('platforms'))
                patterns.append(Pattern(
                    name=p['name'],
                    regex=p['regex'],
                    severity=p['severity'],
                    description=p['description'],
                    module=module_name,
                    platforms=platforms
                ))

    return patterns


def detect_line_platform(line: str) -> PlatformType:
    """检测单行日志的平台类型"""
    line = line.strip()

    # 跳过分隔行
    if line.startswith('--------- beginning of'):
        return PlatformType.UNKNOWN

    # Android STB ROM: 带TID的logcat格式
    # 01-01 08:00:00.312  2069  2069 W auditd  :
    if re.match(r'^\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s+\d+\s+\d+\s+[VDIWEF]\s+', line):
        return PlatformType.ANDROID_STB_ROM

    # Android TV: 标准logcat格式
    # 03-09 16:00:46.289 D/aml_hal_core_detect( 395):
    if re.match(r'^\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s+[VDIWEF]/', line):
        return PlatformType.ANDROID_TV

    # Linux STB: iPanel格式
    # [I][93][porting_display_init:78](in)
    # [tm=52][tid:40bdf2b0]
    if re.match(r'^\[([VDIWEF])\]', line) or re.match(r'^\[tm=', line):
        return PlatformType.LINUX_STB

    return PlatformType.UNKNOWN


def detect_file_platform(filepath: str, sample_lines: int = 100) -> PlatformType:
    """检测日志文件的主要平台类型"""
    counts = {pt: 0 for pt in PlatformType}

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i >= sample_lines:
                break
            platform = detect_line_platform(line)
            counts[platform] += 1

    counts.pop(PlatformType.UNKNOWN)
    if not counts or max(counts.values()) == 0:
        return PlatformType.UNKNOWN

    return max(counts, key=counts.get)


def match_pattern(line: str, pattern: Pattern, line_platform: PlatformType = None) -> Optional[Match]:
    """Check if line matches a pattern"""
    # 检查平台兼容性
    if pattern.platforms and line_platform:
        if line_platform not in pattern.platforms:
            return None

    try:
        regex = re.compile(pattern.regex, re.IGNORECASE)
        match = regex.search(line)
        if match:
            return Match(
                pattern=pattern,
                line_number=0,
                line_content=line,
                matched_text=match.group(0),
                platform=line_platform or PlatformType.UNKNOWN
            )
    except re.error:
        pass  # Invalid regex, skip
    return None


def scan_file(filepath: str, patterns: list[Pattern] = None, config: dict = None,
              platform_filter: PlatformType = None) -> list[Match]:
    """
    Scan file for all pattern matches

    Args:
        filepath: 日志文件路径
        patterns: 模式列表
        config: 配置字典
        platform_filter: 平台过滤器，只返回该平台的匹配
    """
    if patterns is None:
        if config is None:
            config = load_config()
        patterns = build_patterns_from_config(config)

    # 检测文件主要平台
    file_platform = detect_file_platform(filepath)

    matches = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            # 检测当前行的平台
            line_platform = detect_line_platform(line)
            if line_platform == PlatformType.UNKNOWN:
                line_platform = file_platform

            # 平台过滤
            if platform_filter and line_platform != platform_filter:
                continue

            for pattern in patterns:
                match = match_pattern(line, pattern, line_platform)
                if match:
                    match.line_number = line_num
                    matches.append(match)

    return matches


def filter_by_module(matches: list[Match], module: str) -> list[Match]:
    """Filter matches by module"""
    return [m for m in matches if m.pattern.module == module]


def filter_by_severity(matches: list[Match], severity: str) -> list[Match]:
    """Filter matches by severity level"""
    return [m for m in matches if m.pattern.severity == severity]


def filter_by_platform(matches: list[Match], platform: PlatformType) -> list[Match]:
    """Filter matches by platform"""
    return [m for m in matches if m.platform == platform]


def group_by_severity(matches: list[Match]) -> dict[str, list[Match]]:
    """Group matches by severity level"""
    groups = {}
    for m in matches:
        sev = m.pattern.severity
        if sev not in groups:
            groups[sev] = []
        groups[sev].append(m)
    return groups


def group_by_module(matches: list[Match]) -> dict[str, list[Match]]:
    """Group matches by module"""
    groups = {}
    for m in matches:
        mod = m.pattern.module or "unknown"
        if mod not in groups:
            groups[mod] = []
        groups[mod].append(m)
    return groups


def group_by_platform(matches: list[Match]) -> dict[PlatformType, list[Match]]:
    """Group matches by platform"""
    groups = {}
    for m in matches:
        plat = m.platform
        if plat not in groups:
            groups[plat] = []
        groups[plat].append(m)
    return groups


def print_report(matches: list[Match], verbose: bool = False, show_platform: bool = True):
    """Print analysis report"""
    if not matches:
        print("No pattern matches found.")
        return

    print(f"Found {len(matches)} pattern matches\n")

    # 平台统计
    if show_platform:
        by_platform = group_by_platform(matches)
        if len(by_platform) > 1 or PlatformType.UNKNOWN not in by_platform:
            print("=" * 50)
            print("平台分布:")
            for plat, plat_matches in by_platform.items():
                print(f"  {plat.value}: {len(plat_matches)} matches")
            print()

    # Group by severity
    by_severity = group_by_severity(matches)
    for sev in ['critical', 'error', 'warning', 'info']:
        if sev in by_severity:
            print(f"\n{'='*20} {sev.upper()} ({len(by_severity[sev])}) {'='*20}")
            for m in by_severity[sev][:10]:
                plat_str = f"[{m.platform.value}]" if show_platform and m.platform != PlatformType.UNKNOWN else ""
                print(f"  L{m.line_number}: {plat_str}[{m.pattern.module}] {m.pattern.name}")
                print(f"       {m.matched_text[:70]}")
                if verbose:
                    print(f"       {m.pattern.description}")

    # Summary by module
    print(f"\n{'='*20} Summary by Module {'='*20}")
    by_module = group_by_module(matches)
    for mod, mod_matches in sorted(by_module.items()):
        print(f"  {mod}: {len(mod_matches)} matches")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Pattern matcher for logcat logs')
    parser.add_argument('logfile', help='Path to log file')
    parser.add_argument('--module', '-m', help='Filter by module (cbn, audio, network, etc.)')
    parser.add_argument('--severity', '-s', help='Filter by severity (critical, error, warning, info)')
    parser.add_argument('--platform', '-p',
                        choices=['android_tv', 'android_stb_rom', 'linux_stb'],
                        help='Filter by platform type')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--config', '-c', help='Path to custom config YAML')
    parser.add_argument('--no-platform', action='store_true', help='Hide platform info in output')

    args = parser.parse_args()

    config = load_config(args.config)
    patterns = build_patterns_from_config(config)

    # 解析平台过滤器
    platform_filter = None
    if args.platform:
        platform_filter = PlatformType(args.platform)

    matches = scan_file(args.logfile, patterns, platform_filter=platform_filter)

    if args.module:
        matches = filter_by_module(matches, args.module)
    if args.severity:
        matches = filter_by_severity(matches, args.severity)

    print_report(matches, args.verbose, show_platform=not args.no_platform)