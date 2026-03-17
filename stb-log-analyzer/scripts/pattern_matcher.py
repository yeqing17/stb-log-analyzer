"""
Pattern Matcher - Match known error patterns in logcat logs

Usage:
    python pattern_matcher.py <logfile>
    python pattern_matcher.py <logfile> --module cbn
    python pattern_matcher.py <logfile> --severity error
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class Pattern:
    """Represents an error pattern"""
    name: str
    regex: str
    severity: str
    description: str
    module: Optional[str] = None


@dataclass
class Match:
    """Represents a pattern match"""
    pattern: Pattern
    line_number: int
    line_content: str
    matched_text: str


def load_config(config_path: str = None) -> dict:
    """Load keywords configuration from YAML file"""
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "keywords.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def build_patterns_from_config(config: dict) -> list[Pattern]:
    """Build Pattern objects from YAML config"""
    patterns = []

    for module_name, module_data in config.items():
        if module_name == 'cases':
            continue  # Skip case index

        if isinstance(module_data, dict) and 'patterns' in module_data:
            for p in module_data['patterns']:
                patterns.append(Pattern(
                    name=p['name'],
                    regex=p['regex'],
                    severity=p['severity'],
                    description=p['description'],
                    module=module_name
                ))

    return patterns


def match_pattern(line: str, pattern: Pattern) -> Optional[Match]:
    """Check if line matches a pattern"""
    try:
        regex = re.compile(pattern.regex, re.IGNORECASE)
        match = regex.search(line)
        if match:
            return Match(
                pattern=pattern,
                line_number=0,
                line_content=line,
                matched_text=match.group(0)
            )
    except re.error:
        pass  # Invalid regex, skip
    return None


def scan_file(filepath: str, patterns: list[Pattern] = None, config: dict = None) -> list[Match]:
    """Scan file for all pattern matches"""
    if patterns is None:
        if config is None:
            config = load_config()
        patterns = build_patterns_from_config(config)

    matches = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            for pattern in patterns:
                match = match_pattern(line, pattern)
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


def print_report(matches: list[Match], verbose: bool = False):
    """Print analysis report"""
    if not matches:
        print("No pattern matches found.")
        return

    print(f"Found {len(matches)} pattern matches\n")

    # Group by severity
    by_severity = group_by_severity(matches)
    for sev in ['critical', 'error', 'warning', 'info']:
        if sev in by_severity:
            print(f"\n{'='*20} {sev.upper()} ({len(by_severity[sev])}) {'='*20}")
            for m in by_severity[sev][:10]:
                print(f"  L{m.line_number}: [{m.pattern.module}] {m.pattern.name}")
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
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--config', '-c', help='Path to custom config YAML')

    args = parser.parse_args()

    config = load_config(args.config)
    patterns = build_patterns_from_config(config)

    matches = scan_file(args.logfile, patterns)

    if args.module:
        matches = filter_by_module(matches, args.module)
    if args.severity:
        matches = filter_by_severity(matches, args.severity)

    print_report(matches, args.verbose)