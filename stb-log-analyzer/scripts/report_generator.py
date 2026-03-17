#!/usr/bin/env python3
"""
STB Log Analyzer - HTML Report Generator
生成日志分析报告的 HTML 版本

支持平台:
- Android TV logcat
- Android STB ROM logcat
- Linux STB
"""

import os
import sys
import yaml
import re
from datetime import datetime
from pathlib import Path
from enum import Enum


class PlatformType(Enum):
    ANDROID_TV = "android_tv"
    ANDROID_STB_ROM = "android_stb_rom"
    LINUX_STB = "linux_stb"
    UNKNOWN = "unknown"


def load_config():
    """加载 keywords.yaml 配置"""
    config_path = Path(__file__).parent / 'config' / 'keywords.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_log_line(line):
    """解析日志行，支持多种格式"""
    # Linux STB 格式: [tm=XXXX][tid:XXXXXXXX] [tag] message
    linux_pattern = r'^\[tm=(\d+)\]\[tid:([0-9a-fA-F]+)\]\s+\[([^\]]+)\]\s*(.*)$'
    match = re.match(linux_pattern, line)
    if match:
        return {
            'timestamp': f'tm={match.group(1)}',
            'pid': '-',
            'tid': match.group(2),
            'level': 'I',  # Linux STB 默认 info
            'tag': match.group(3).strip(),
            'message': match.group(4),
            'platform': PlatformType.LINUX_STB
        }

    # Android STB ROM 格式: MM-DD HH:MM:SS.mmm PID TID Level Tag: Message
    stb_pattern = r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+([^\s:]+)\s*:\s*(.*)$'
    match = re.match(stb_pattern, line)
    if match:
        return {
            'timestamp': match.group(1),
            'pid': match.group(2),
            'tid': match.group(3),
            'level': match.group(4),
            'tag': match.group(5).strip(),
            'message': match.group(6),
            'platform': PlatformType.ANDROID_STB_ROM
        }

    # Android TV 格式: MM-DD HH:MM:SS.mmm Level/Tag(PID): Message
    tv_pattern = r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+([VDIWEF])/([^\(]+)\(\s*(\d+)\):\s*(.*)$'
    match = re.match(tv_pattern, line)
    if match:
        return {
            'timestamp': match.group(1),
            'level': match.group(2),
            'tag': match.group(3).strip(),
            'pid': match.group(4),
            'tid': None,
            'message': match.group(5),
            'platform': PlatformType.ANDROID_TV
        }
    return None


def detect_platform(log_path, sample_lines=100):
    """检测日志文件的平台类型"""
    counts = {PlatformType.ANDROID_TV: 0, PlatformType.ANDROID_STB_ROM: 0, PlatformType.LINUX_STB: 0}

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i >= sample_lines:
                break
            parsed = parse_log_line(line)
            if parsed:
                counts[parsed['platform']] += 1

    if max(counts.values()) == 0:
        return PlatformType.UNKNOWN
    return max(counts, key=counts.get)


def detect_platform_simple(log_path, sample_lines=200):
    """简单平台检测 - 直接检查特征"""
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [f.readline() for _ in range(sample_lines)]
        sample = ''.join(lines)

    # Linux STB 特征检查 (多种格式)
    # 1. iPanel 格式: [tm=XXXX][tid:XXXXXXXX]
    # 2. Linux porting 格式: [I][93][porting_xxx]
    # 3. ERROR-ao 等 Linux 错误格式
    linux_patterns = [
        r'\[tm=\d+\]\[tid:[0-9a-fA-F]+\]',  # iPanel 格式
        r'\[[IWEF]\]\[\d+\]\[porting_',     # porting 格式
        r'ERROR-ao',                         # Linux audio error
        r'\[XINJIANG\]',                     # 项目标识
        r'iPanel',                           # iPanel 中间件
        r'PLATFORM:\[HI\d+\]',               # HiSilicon 平台
    ]
    for pattern in linux_patterns:
        if re.search(pattern, sample):
            return PlatformType.LINUX_STB

    # Android STB ROM 特征: PID TID Level Tag 格式
    if re.search(r'^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+\d+\s+\d+\s+[VDIWEF]\s+', sample, re.MULTILINE):
        return PlatformType.ANDROID_STB_ROM

    # Android TV 特征: Level/Tag(PID) 格式
    if re.search(r'^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+[VDIWEF]/.+\(\s*\d+\):', sample, re.MULTILINE):
        return PlatformType.ANDROID_TV

    return PlatformType.UNKNOWN


def analyze_login_flow(log_path):
    """分析登录流程 - 支持 Android 和 Linux STB"""
    results = {
        'homed_login': None,
        'homed_user_list': None,
        'cbn_init': None,
        'cbn_login': None,
        'dongle_status': None,
        'device_auth': None,
        'tabcards': [],
        'device_info': {},
        'errors': [],
        'warnings': [],
        'platform': None
    }

    # 先检测平台
    results['platform'] = detect_platform_simple(log_path)

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            parsed = parse_log_line(line)

            # === Linux STB 特有检测 ===
            if results['platform'] == PlatformType.LINUX_STB:
                # Linux STB Web 登录页面加载
                if 'login.php' in line and 'open url' in line:
                    results['homed_login'] = {
                        'status': 'loading',
                        'time': parsed['timestamp'] if parsed else 'Unknown',
                        'line': line_num
                    }

                # Linux STB 登录成功 - 获取到用户数据
                if 'home_id:' in line or ('PUT_VALUE' in line and 'home_id' in line):
                    match = re.search(r'home_id[\":\s]*(\d+)', line)
                    if match:
                        results['homed_user_list'] = {
                            'status': 'success',
                            'time': parsed['timestamp'] if parsed else 'Unknown',
                            'line': line_num
                        }
                        results['device_info']['home_id'] = match.group(1)

                # Linux STB 用户信息
                if 'nick_name:' in line or ('PUT_VALUE' in line and 'nick_name' in line):
                    match = re.search(r'nick_name[\":\s]*([^\s,\]]+)', line)
                    if match and match.group(1) not in ['nick_name']:
                        results['cbn_login'] = {
                            'status': 'success',
                            'time': parsed['timestamp'] if parsed else 'Unknown',
                            'line': line_num
                        }
                        results['device_info']['nick_name'] = match.group(1)

                # Linux STB device_id
                if 'device_id:' in line or ('PUT_VALUE' in line and 'device_id' in line):
                    match = re.search(r'device_id[\":\s]*(\d+)', line)
                    if match:
                        results['device_info']['oid'] = match.group(1)

                # Linux STB 首页数据 - portal/get_list
                if 'application/portal/get_list' in line or ('name:/application/portal/get_list' in line):
                    results['tabcards'].append({
                        'size': 1,
                        'time': parsed['timestamp'] if parsed else 'Unknown',
                        'line': line_num
                    })

                # Linux STB 错误
                if 'ERROR' in line or 'error' in line.lower():
                    if parsed and len(line) < 500:
                        results['errors'].append({
                            'line': line_num,
                            'time': parsed.get('timestamp', '--'),
                            'tag': parsed.get('tag', '--'),
                            'message': parsed.get('message', line[:200])
                        })

                continue  # 跳过 Android 检测

            # === Android 平台检测 ===
            # account/login
            if 'account/login' in line and 'response' in line:
                results['homed_login'] = {
                    'status': 'success',
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                }

            # user/get_list
            if 'user/get_list' in line and 'response' in line:
                results['homed_user_list'] = {
                    'status': 'success',
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                }

            # GwSDK initSDK
            match = re.search(r'GwSDK.*initSDK env\s*=\s*(\w+).*province\s*=\s*(\w+)', line)
            if match:
                results['cbn_init'] = {
                    'status': 'success',
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                }
                results['device_info']['env'] = match.group(1)
                results['device_info']['province'] = match.group(2)

            # onLoginSuccess
            if 'onLoginSuccess' in line:
                results['cbn_login'] = {
                    'status': 'success',
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                }

            # onLoginError
            if 'onLoginError' in line:
                results['cbn_login'] = {
                    'status': 'error',
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                }

            # Dongle alive
            match = re.search(r'usb\.idongle\.alive\s*=\s*\[([^\]]*)\]', line)
            if match:
                devices = match.group(1).strip()
                results['dongle_status'] = 'connected' if devices else 'none'

            # deviceAuthByLocalDevice
            if 'deviceAuthByLocalDevice' in line:
                results['device_auth'] = 'local'
                match = re.search(r'deviceNo\s*=\s*(\S+)', line)
                if match:
                    results['device_info']['oid'] = match.group(1)

            # deviceAuth true
            if 'deviceAuth true' in line:
                results['device_auth'] = 'dongle'

            # oid/caid
            match = re.search(r'oid=([^,]*),\s*caid=([^,\s]*)', line)
            if match:
                oid, caid = match.groups()
                if oid != 'null' and caid != 'null':
                    results['device_info']['oid'] = oid
                    results['device_info']['caid'] = caid

            # TabCards
            match = re.search(r'onGetTabCards list\.size:(\d+)', line)
            if match:
                results['tabcards'].append({
                    'size': int(match.group(1)),
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                })

            # 收集错误
            if re.search(r'\s[E]\s', line) or 'ERROR' in line:
                if parsed and len(line) < 500:
                    results['errors'].append({
                        'line': line_num,
                        'time': parsed.get('timestamp', '--'),
                        'tag': parsed.get('tag', '--'),
                        'message': parsed.get('message', line[:200])
                    })

            # 收集警告
            if re.search(r'\s[W]\s', line) or 'WARNING' in line:
                if parsed and len(line) < 500:
                    results['warnings'].append({
                        'line': line_num,
                        'time': parsed.get('timestamp', '--'),
                        'tag': parsed.get('tag', '--'),
                        'message': parsed.get('message', line[:200])
                    })

    return results


def scan_patterns(log_path, config, platform=None):
    """扫描日志中的模式匹配"""
    matches = []

    # 平台字符串映射
    platform_str = platform.value if platform else None

    # 构建模式列表
    patterns = []
    for module_name, module_data in config.items():
        if module_name == 'cases':
            continue
        if isinstance(module_data, dict) and 'patterns' in module_data:
            for p in module_data['patterns']:
                # 检查平台过滤
                if 'platforms' in p:
                    if platform_str and platform_str not in p['platforms']:
                        continue
                patterns.append({
                    'name': p['name'],
                    'regex': p['regex'],
                    'severity': p['severity'],
                    'description': p['description'],
                    'module': module_name
                })

    # 扫描
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            for pattern in patterns:
                try:
                    if re.search(pattern['regex'], line, re.IGNORECASE):
                        matches.append({
                            'line': line_num,
                            'pattern': pattern,
                            'text': line[:200]
                        })
                except re.error:
                    pass

    return matches


def generate_html_report(log_path, output_path=None):
    """生成 HTML 报告"""
    log_path = Path(log_path)
    if not log_path.exists():
        print(f"Error: Log file not found: {log_path}")
        return None

    # 检测平台
    platform = detect_platform_simple(log_path)

    # 分析日志
    login_results = analyze_login_flow(log_path)

    # 模式匹配
    config = load_config()
    pattern_matches = scan_patterns(log_path, config, platform)

    # 统计模式匹配
    module_stats = {}
    severity_stats = {'critical': 0, 'error': 0, 'warning': 0, 'info': 0}
    for m in pattern_matches:
        mod = m['pattern']['module']
        sev = m['pattern']['severity']
        module_stats[mod] = module_stats.get(mod, 0) + 1
        severity_stats[sev] = severity_stats.get(sev, 0) + 1

    # 确定整体状态 (根据平台不同判断)
    if platform == PlatformType.LINUX_STB:
        all_success = (
            login_results['homed_user_list'] is not None and
            login_results['cbn_login'] is not None and
            login_results['cbn_login']['status'] == 'success'
        )
    else:
        all_success = (
            login_results['homed_login'] and
            login_results['cbn_login'] and
            login_results['cbn_login']['status'] == 'success' and
            len(login_results['tabcards']) > 0
        )

    # 生成 HTML
    html = generate_full_html(
        log_path=log_path,
        platform=platform,
        login_results=login_results,
        pattern_matches=pattern_matches,
        module_stats=module_stats,
        severity_stats=severity_stats,
        all_success=all_success
    )

    # 输出路径
    if output_path is None:
        reports_dir = Path(__file__).parent.parent.parent / 'reports'
        reports_dir.mkdir(exist_ok=True)
        output_path = reports_dir / f"{log_path.stem}_report.html"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path


def generate_full_html(log_path, platform, login_results, pattern_matches, module_stats, severity_stats, all_success):
    """生成完整的 HTML 报告"""

    summary_color = 'success' if all_success else 'error'
    summary_icon = '✓' if all_success else '✗'
    summary_text = '登录状态: 全部成功' if all_success else '登录状态: 存在问题'

    # 设备信息 - 根据 platform 类型显示不同内容
    is_linux = platform == PlatformType.LINUX_STB
    if is_linux:
        device_info = f"iPanel / {login_results['device_info'].get('home_id', 'Unknown')}"
        device_id = login_results['device_info'].get('oid', 'Unknown')
    else:
        device_info = f"{login_results['device_info'].get('province', 'Unknown')} / {login_results['device_info'].get('env', 'Unknown')}"
        device_id = login_results['device_info'].get('oid', 'Unknown')

    # 生成流程图
    flow_html = generate_flow_diagram(login_results)

    # 生成登录表格
    login_table_html = generate_login_table(login_results)

    # 生成时序
    timeline_html = generate_timeline(login_results)

    # 生成统计表格
    stats_html = generate_stats_table(module_stats, severity_stats)

    # 生成问题列表
    issues_html = generate_issues(pattern_matches, login_results)

    # 生成结论
    conclusion_html = generate_conclusion(login_results, all_success)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>日志分析报告 - {log_path.name}</title>
    <style>
        :root {{
            --success: #10b981;
            --error: #ef4444;
            --warning: #f59e0b;
            --info: #3b82f6;
            --bg: #f8fafc;
            --card: #ffffff;
            --border: #e2e8f0;
            --text: #1e293b;
            --text-light: #64748b;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .header .meta {{ opacity: 0.9; font-size: 14px; }}
        .header .platform-badge {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 20px;
            margin-top: 8px;
            font-size: 13px;
        }}
        .summary-box {{
            background: var(--card);
            border: 2px solid var(--{summary_color});
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .summary-box .icon {{
            width: 48px; height: 48px;
            background: var(--{summary_color});
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 24px; color: white;
        }}
        .summary-box .status {{
            font-size: 20px; font-weight: 600;
            color: var(--{summary_color});
        }}
        .card {{
            background: var(--card);
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
            overflow: hidden;
        }}
        .card-header {{
            background: #f1f5f9;
            padding: 16px 20px;
            font-weight: 600;
            border-bottom: 1px solid var(--border);
        }}
        .card-body {{ padding: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background: #f8fafc; font-weight: 600; font-size: 13px; color: var(--text-light); }}
        tr:last-child td {{ border-bottom: none; }}
        .status-badge {{
            display: inline-flex; align-items: center; gap: 6px;
            padding: 4px 12px; border-radius: 20px;
            font-size: 13px; font-weight: 500;
        }}
        .status-badge.success {{ background: #dcfce7; color: #166534; }}
        .status-badge.error {{ background: #fee2e2; color: #991b1b; }}
        .status-badge.warning {{ background: #fef3c7; color: #92400e; }}
        .status-badge.info {{ background: #dbeafe; color: #1e40af; }}
        .flow-diagram {{
            display: flex; align-items: center; justify-content: center;
            gap: 8px; flex-wrap: wrap;
            padding: 20px; background: #f8fafc; border-radius: 8px;
        }}
        .flow-step {{
            background: white; border: 2px solid var(--border);
            padding: 12px 20px; border-radius: 8px; text-align: center;
            min-width: 100px;
        }}
        .flow-step.success {{ border-color: var(--success); background: #f0fdf4; }}
        .flow-step.error {{ border-color: var(--error); background: #fef2f2; }}
        .flow-arrow {{ color: var(--text-light); font-size: 20px; }}
        .timeline {{ position: relative; padding-left: 24px; }}
        .timeline::before {{
            content: ''; position: absolute;
            left: 8px; top: 0; bottom: 0;
            width: 2px; background: var(--border);
        }}
        .timeline-item {{ position: relative; padding-bottom: 16px; display: flex; gap: 12px; align-items: baseline; }}
        .timeline-item::before {{
            content: ''; position: absolute;
            left: -20px; top: 6px;
            width: 10px; height: 10px; border-radius: 50%;
            background: var(--info); border: 2px solid white;
        }}
        .timeline-item.success::before {{ background: var(--success); }}
        .timeline-item.error::before {{ background: var(--error); }}
        .timeline-item.warning::before {{ background: var(--warning); }}
        .timeline-time {{ font-family: monospace; font-size: 13px; color: var(--text-light); min-width: 120px; }}
        .timeline-event {{ font-weight: 500; flex: 1; }}
        .timeline-stage {{
            font-size: 12px; color: var(--text-light);
            background: #f1f5f9; padding: 2px 8px; border-radius: 4px;
        }}
        .log-block {{
            background: #1e293b; color: #e2e8f0;
            padding: 16px; border-radius: 8px;
            font-family: 'SF Mono', Monaco, monospace; font-size: 12px;
            overflow-x: auto; white-space: pre-wrap;
            margin-top: 8px;
        }}
        .issue-item {{
            background: #fef2f2; border-left: 4px solid var(--error);
            padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 16px;
        }}
        .issue-item.warning {{ background: #fffbeb; border-color: var(--warning); }}
        .issue-title {{ font-weight: 600; margin-bottom: 8px; }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 16px;
        }}
        .metric-card {{
            background: #f8fafc; border-radius: 8px;
            padding: 16px; text-align: center;
        }}
        .metric-value {{ font-size: 24px; font-weight: 700; }}
        .metric-value.critical {{ color: var(--error); }}
        .metric-value.error {{ color: #dc2626; }}
        .metric-value.warning {{ color: var(--warning); }}
        .metric-value.info {{ color: var(--info); }}
        .metric-label {{ font-size: 13px; color: var(--text-light); margin-top: 4px; }}
        .footer {{
            text-align: center; padding: 20px;
            color: var(--text-light); font-size: 13px;
        }}
        code {{
            background: #f1f5f9; padding: 2px 6px;
            border-radius: 4px; font-family: monospace; font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📋 日志分析报告</h1>
            <div class="meta">
                <strong>文件:</strong> {log_path.name} &nbsp;|&nbsp;
                <strong>设备:</strong> {device_info} &nbsp;|&nbsp;
                <strong>分析时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}
            </div>
            <div class="platform-badge">🖥️ 平台: {platform.value}</div>
        </div>

        <!-- Summary -->
        <div class="summary-box">
            <div class="icon">{summary_icon}</div>
            <div class="text">
                <div class="status">{summary_text}</div>
                <div style="color: var(--text-light); margin-top: 4px;">
                    设备ID: <code>{device_id}</code>
                </div>
            </div>
        </div>

        <!-- Login Flow -->
        <div class="card">
            <div class="card-header">🔐 登录流程检查</div>
            <div class="card-body">
                <div class="flow-diagram">
                    {flow_html}
                </div>
                <table style="margin-top: 20px;">
                    <thead>
                        <tr>
                            <th>阶段</th>
                            <th>状态</th>
                            <th>关键日志</th>
                            <th>详情</th>
                        </tr>
                    </thead>
                    <tbody>
                        {login_table_html}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Timeline -->
        <div class="card">
            <div class="card-header">⏱️ 时序分析</div>
            <div class="card-body">
                <div class="timeline">
                    {timeline_html}
                </div>
            </div>
        </div>

        <!-- Statistics -->
        <div class="card">
            <div class="card-header">📊 模式匹配统计</div>
            <div class="card-body">
                <div class="metrics">
                    <div class="metric-card">
                        <div class="metric-value critical">{severity_stats['critical']}</div>
                        <div class="metric-label">Critical</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value error">{severity_stats['error']}</div>
                        <div class="metric-label">Error</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value warning">{severity_stats['warning']}</div>
                        <div class="metric-label">Warning</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value info">{severity_stats['info']}</div>
                        <div class="metric-label">Info</div>
                    </div>
                </div>
                <table style="margin-top: 20px;">
                    <thead>
                        <tr>
                            <th>模块</th>
                            <th>匹配数</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stats_html}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Issues -->
        <div class="card">
            <div class="card-header">⚠️ 发现的问题</div>
            <div class="card-body">
                {issues_html}
            </div>
        </div>

        <!-- Conclusion -->
        <div class="card">
            <div class="card-header">📝 结论</div>
            <div class="card-body">
                {conclusion_html}
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            Generated by STB Log Analyzer | {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
    </div>
</body>
</html>'''


def generate_flow_diagram(login_results):
    """生成流程图 HTML - 支持 Linux STB 和 Android"""
    steps = []
    is_linux = login_results.get('platform') == PlatformType.LINUX_STB

    if is_linux:
        # Linux STB 流程: Web登录页 → Homed API → 用户数据 → 首页数据
        if login_results['homed_login']:
            steps.append('<div class="flow-step success">Web 登录页<br><small style="color: var(--success);">✓ 已加载</small></div>')
        else:
            steps.append('<div class="flow-step">Web 登录页<br><small>未检测</small></div>')

        steps.append('<span class="flow-arrow">→</span>')

        if login_results['homed_user_list']:
            steps.append('<div class="flow-step success">Homed API<br><small style="color: var(--success);">✓ 成功</small></div>')
        else:
            steps.append('<div class="flow-step">Homed API<br><small>未检测</small></div>')

        steps.append('<span class="flow-arrow">→</span>')

        if login_results['cbn_login'] and login_results['cbn_login']['status'] == 'success':
            steps.append('<div class="flow-step success">用户数据<br><small style="color: var(--success);">✓ 已获取</small></div>')
        elif login_results['cbn_login']:
            steps.append('<div class="flow-step error">用户数据<br><small style="color: var(--error);">✗ 失败</small></div>')
        else:
            steps.append('<div class="flow-step">用户数据<br><small>未获取</small></div>')

        steps.append('<span class="flow-arrow">→</span>')

        if login_results['tabcards']:
            steps.append(f'<div class="flow-step success">首页数据<br><small style="color: var(--success);">✓ 已加载</small></div>')
        else:
            steps.append('<div class="flow-step">首页数据<br><small>未检测</small></div>')
    else:
        # Android 流程
        # Dongle
        if login_results['dongle_status'] == 'none':
            steps.append('<div class="flow-step error">USB Dongle<br><small style="color: var(--error);">❌ 无设备</small></div>')
        elif login_results['dongle_status'] == 'connected':
            steps.append('<div class="flow-step success">USB Dongle<br><small style="color: var(--success);">✓ 已连接</small></div>')
        else:
            steps.append('<div class="flow-step">USB Dongle<br><small>未检测</small></div>')

        steps.append('<span class="flow-arrow">→</span>')

        # 认证方式
        if login_results['device_auth'] == 'local':
            steps.append('<div class="flow-step success">本地认证<br><small style="color: var(--success);">✓ 本地设备ID</small></div>')
        elif login_results['device_auth'] == 'dongle':
            steps.append('<div class="flow-step success">Dongle认证<br><small style="color: var(--success);">✓ deviceAuth</small></div>')
        else:
            steps.append('<div class="flow-step">认证方式<br><small>未检测</small></div>')

        steps.append('<span class="flow-arrow">→</span>')

        # Homed
        if login_results['homed_login']:
            steps.append('<div class="flow-step success">Homed 登录<br><small style="color: var(--success);">✓ 成功</small></div>')
        else:
            steps.append('<div class="flow-step">Homed 登录<br><small>未检测</small></div>')

        steps.append('<span class="flow-arrow">→</span>')

        # CBN
        if login_results['cbn_login'] and login_results['cbn_login']['status'] == 'success':
            steps.append('<div class="flow-step success">CBN 登录<br><small style="color: var(--success);">✓ onLoginSuccess</small></div>')
        elif login_results['cbn_login']:
            steps.append('<div class="flow-step error">CBN 登录<br><small style="color: var(--error);">✗ onLoginError</small></div>')
        else:
            steps.append('<div class="flow-step">CBN 登录<br><small>未检测</small></div>')

        steps.append('<span class="flow-arrow">→</span>')

        # 首页数据
        if login_results['tabcards']:
            steps.append(f'<div class="flow-step success">首页数据<br><small style="color: var(--success);">✓ {len(login_results["tabcards"])}次</small></div>')
        else:
            steps.append('<div class="flow-step">首页数据<br><small>未获取</small></div>')

    return '\n'.join(steps)


def generate_login_table(login_results):
    """生成登录表格 HTML - 支持 Linux STB 和 Android"""
    rows = []
    is_linux = login_results.get('platform') == PlatformType.LINUX_STB

    if is_linux:
        # Linux STB 表格
        # Web 登录页
        if login_results['homed_login']:
            rows.append(f'<tr><td>Web 登录页</td><td><span class="status-badge success">✓ 已加载</span></td><td><code>login.php</code></td><td>{login_results["homed_login"]["time"]}</td></tr>')
        else:
            rows.append('<tr><td>Web 登录页</td><td><span class="status-badge info">未检测</span></td><td>-</td><td>-</td></tr>')

        # Homed API
        if login_results['homed_user_list']:
            home_id = login_results['device_info'].get('home_id', '-')
            rows.append(f'<tr><td>Homed API</td><td><span class="status-badge success">✓ 成功</span></td><td><code>account/user/get_list</code></td><td>home_id: {home_id}</td></tr>')
        else:
            rows.append('<tr><td>Homed API</td><td><span class="status-badge error">✗ 未检测到</span></td><td>-</td><td>-</td></tr>')

        # 用户数据
        if login_results['cbn_login'] and login_results['cbn_login']['status'] == 'success':
            nick_name = login_results['device_info'].get('nick_name', '-')
            rows.append(f'<tr><td>用户数据</td><td><span class="status-badge success">✓ 已获取</span></td><td><code>nick_name</code></td><td>{nick_name}</td></tr>')
        elif login_results['cbn_login']:
            rows.append('<tr><td>用户数据</td><td><span class="status-badge error">✗ 失败</span></td><td>-</td><td>-</td></tr>')
        else:
            rows.append('<tr><td>用户数据</td><td><span class="status-badge error">✗ 未获取</span></td><td>-</td><td>-</td></tr>')

        # 首页数据
        if login_results['tabcards']:
            rows.append('<tr><td>首页数据</td><td><span class="status-badge success">✓ 已加载</span></td><td><code>portal/get_list</code></td><td>门户数据</td></tr>')
        else:
            rows.append('<tr><td>首页数据</td><td><span class="status-badge info">未检测</span></td><td>-</td><td>-</td></tr>')

        # 设备 ID
        device_id = login_results['device_info'].get('oid', 'Unknown')
        rows.append(f'<tr><td>设备 ID</td><td><span class="status-badge info">-</span></td><td><code>device_id</code></td><td>{device_id}</td></tr>')

    else:
        # Android 表格
        # Dongle
        if login_results['dongle_status'] == 'none':
            rows.append('<tr><td>USB Dongle</td><td><span class="status-badge error">❌ 无设备</span></td><td><code>usb.idongle.alive = []</code></td><td>无 Dongle，使用本地认证</td></tr>')
        elif login_results['dongle_status'] == 'connected':
            rows.append('<tr><td>USB Dongle</td><td><span class="status-badge success">✓ 已连接</span></td><td><code>usb.idongle.alive</code></td><td>Dongle 已识别</td></tr>')
        else:
            rows.append('<tr><td>USB Dongle</td><td><span class="status-badge info">未检测</span></td><td>-</td><td>-</td></tr>')

        # 认证方式
        if login_results['device_auth'] == 'local':
            rows.append('<tr><td>设备认证</td><td><span class="status-badge success">✓ 成功</span></td><td><code>deviceAuthByLocalDevice</code></td><td>本地设备认证</td></tr>')
        elif login_results['device_auth'] == 'dongle':
            rows.append('<tr><td>设备认证</td><td><span class="status-badge success">✓ 成功</span></td><td><code>deviceAuth true</code></td><td>Dongle 认证</td></tr>')
        else:
            rows.append('<tr><td>设备认证</td><td><span class="status-badge info">未检测</span></td><td>-</td><td>-</td></tr>')

        # Homed 登录
        if login_results['homed_login']:
            rows.append(f'<tr><td>Homed 登录</td><td><span class="status-badge success">✓ 成功</span></td><td><code>account/login</code></td><td>{login_results["homed_login"]["time"]}</td></tr>')
        else:
            rows.append('<tr><td>Homed 登录</td><td><span class="status-badge error">✗ 未检测到</span></td><td>-</td><td>-</td></tr>')

        # CBN 初始化
        if login_results['cbn_init']:
            env = login_results['device_info'].get('env', '-')
            province = login_results['device_info'].get('province', '-')
            rows.append(f'<tr><td>CBN 初始化</td><td><span class="status-badge success">✓ 成功</span></td><td><code>GwSDK.initSDK</code></td><td>{env}, {province}</td></tr>')
        else:
            rows.append('<tr><td>CBN 初始化</td><td><span class="status-badge info">未检测</span></td><td>-</td><td>-</td></tr>')

        # CBN 登录
        if login_results['cbn_login'] and login_results['cbn_login']['status'] == 'success':
            rows.append(f'<tr><td>CBN 登录</td><td><span class="status-badge success">✓ 成功</span></td><td><code>onLoginSuccess</code></td><td>{login_results["cbn_login"]["time"]}</td></tr>')
        elif login_results['cbn_login']:
            rows.append(f'<tr><td>CBN 登录</td><td><span class="status-badge error">✗ 失败</span></td><td><code>onLoginError</code></td><td>{login_results["cbn_login"]["time"]}</td></tr>')
        else:
            rows.append('<tr><td>CBN 登录</td><td><span class="status-badge error">✗ 未检测到</span></td><td>-</td><td>-</td></tr>')

        # 首页数据
        if login_results['tabcards']:
            sizes = [str(t['size']) for t in login_results['tabcards']]
            tabcards_text = f"多次获取 ({'/'.join(sizes[:3])}条)"
            rows.append(f'<tr><td>首页数据</td><td><span class="status-badge success">✓ 成功</span></td><td><code>onGetTabCards</code></td><td>{tabcards_text}</td></tr>')
        else:
            rows.append('<tr><td>首页数据</td><td><span class="status-badge error">✗ 未获取</span></td><td>-</td><td>-</td></tr>')

    return '\n'.join(rows)


def generate_timeline(login_results):
    """生成时序 HTML - 支持 Linux STB 和 Android"""
    items = []
    is_linux = login_results.get('platform') == PlatformType.LINUX_STB

    if is_linux:
        # Linux STB 时序
        if login_results['homed_login']:
            items.append(f'<div class="timeline-item"><span class="timeline-time">{login_results["homed_login"]["time"]}</span><span class="timeline-event">Web 登录页加载</span><span class="timeline-stage">初始化</span></div>')

        if login_results['homed_user_list']:
            items.append(f'<div class="timeline-item success"><span class="timeline-time">{login_results["homed_user_list"]["time"]}</span><span class="timeline-event"><strong>Homed API 响应</strong></span><span class="timeline-stage">Homed</span></div>')

        if login_results['cbn_login']:
            status_class = 'success' if login_results['cbn_login']['status'] == 'success' else 'error'
            nick_name = login_results['device_info'].get('nick_name', '')
            items.append(f'<div class="timeline-item {status_class}"><span class="timeline-time">{login_results["cbn_login"]["time"]}</span><span class="timeline-event"><strong>用户数据获取: {nick_name}</strong></span><span class="timeline-stage">用户</span></div>')

        for tc in login_results['tabcards'][:3]:
            items.append(f'<div class="timeline-item success"><span class="timeline-time">{tc["time"]}</span><span class="timeline-event">首页数据加载</span><span class="timeline-stage">数据</span></div>')
    else:
        # Android 时序
        if login_results['dongle_status'] == 'none':
            items.append('<div class="timeline-item error"><span class="timeline-time">--</span><span class="timeline-event">Dongle 检查: 无设备</span><span class="timeline-stage">Dongle</span></div>')
        elif login_results['dongle_status'] == 'connected':
            items.append('<div class="timeline-item success"><span class="timeline-time">--</span><span class="timeline-event">Dongle 检查: 已连接</span><span class="timeline-stage">Dongle</span></div>')

        if login_results['device_auth'] == 'local':
            items.append('<div class="timeline-item success"><span class="timeline-time">--</span><span class="timeline-event">切换本地设备认证</span><span class="timeline-stage">认证</span></div>')

        if login_results['homed_login']:
            items.append(f'<div class="timeline-item success"><span class="timeline-time">{login_results["homed_login"]["time"]}</span><span class="timeline-event">Homed 登录成功</span><span class="timeline-stage">Homed</span></div>')

        if login_results['cbn_init']:
            items.append(f'<div class="timeline-item"><span class="timeline-time">{login_results["cbn_init"]["time"]}</span><span class="timeline-event">GwSDK.initSDK 开始</span><span class="timeline-stage">CBN</span></div>')

        if login_results['cbn_login']:
            status_class = 'success' if login_results['cbn_login']['status'] == 'success' else 'error'
            status_text = '成功' if login_results['cbn_login']['status'] == 'success' else '失败'
            items.append(f'<div class="timeline-item {status_class}"><span class="timeline-time">{login_results["cbn_login"]["time"]}</span><span class="timeline-event"><strong>{"onLoginSuccess" if login_results["cbn_login"]["status"] == "success" else "onLoginError"}</strong></span><span class="timeline-stage">CBN {status_text}</span></div>')

        for tc in login_results['tabcards'][:3]:
            items.append(f'<div class="timeline-item success"><span class="timeline-time">{tc["time"]}</span><span class="timeline-event">onGetTabCards list.size:{tc["size"]}</span><span class="timeline-stage">数据加载</span></div>')

    return '\n'.join(items)


def generate_stats_table(module_stats, severity_stats):
    """生成统计表格 HTML"""
    rows = []
    for mod, count in sorted(module_stats.items(), key=lambda x: -x[1]):
        rows.append(f'<tr><td><code>{mod}</code></td><td><strong>{count}</strong></td></tr>')
    return '\n'.join(rows)


def generate_issues(pattern_matches, login_results):
    """生成问题列表 HTML"""
    items = []

    # 按严重级别分组
    critical_errors = [m for m in pattern_matches if m['pattern']['severity'] == 'critical'][:5]
    errors = [m for m in pattern_matches if m['pattern']['severity'] == 'error'][:10]
    warnings = [m for m in pattern_matches if m['pattern']['severity'] == 'warning'][:5]

    for m in critical_errors:
        items.append(f'''
            <div class="issue-item">
                <div class="issue-title">🔴 [{m['pattern']['module']}] {m['pattern']['name']} (Critical)</div>
                <p style="color: var(--text-light); margin-bottom: 8px;">{m['pattern']['description']}</p>
                <p><strong>位置:</strong> L{m['line']}</p>
                <div class="log-block">{m['text'][:300]}</div>
            </div>
        ''')

    for m in errors:
        items.append(f'''
            <div class="issue-item">
                <div class="issue-title">🟠 [{m['pattern']['module']}] {m['pattern']['name']} (Error)</div>
                <p style="color: var(--text-light); margin-bottom: 8px;">{m['pattern']['description']}</p>
                <p><strong>位置:</strong> L{m['line']}</p>
            </div>
        ''')

    for m in warnings:
        items.append(f'''
            <div class="issue-item warning">
                <div class="issue-title">🟡 [{m['pattern']['module']}] {m['pattern']['name']} (Warning)</div>
                <p style="color: var(--text-light);">{m['pattern']['description']}</p>
            </div>
        ''')

    if not items:
        items.append('<p style="color: var(--success);">✓ 未发现严重问题</p>')

    return '\n'.join(items)


def generate_conclusion(login_results, all_success):
    """生成结论 HTML - 支持 Linux STB 和 Android"""
    is_linux = login_results.get('platform') == PlatformType.LINUX_STB

    if all_success:
        if is_linux:
            nick_name = login_results['device_info'].get('nick_name', 'Unknown')
            home_id = login_results['device_info'].get('home_id', 'Unknown')
            return f'''
                <p style="font-size: 16px;">该 Linux STB 设备登录流程<strong style="color: var(--success);">完全正常</strong>：</p>
                <ol style="margin-top: 12px; margin-left: 20px;">
                    <li>Web 登录页加载成功</li>
                    <li>Homed API 调用成功</li>
                    <li>用户数据获取成功 (nick_name: {nick_name})</li>
                    <li>home_id: {home_id}</li>
                </ol>
                <div style="margin-top: 16px; padding: 12px; background: #dbeafe; border-radius: 8px;">
                    <strong>平台:</strong> <code>Linux STB (iPanel 中间件)</code>
                </div>
            '''
        else:
            if login_results['dongle_status'] == 'none':
                return '''
                    <p style="font-size: 16px;">该设备登录流程<strong style="color: var(--success);">完全正常</strong>：</p>
                    <ol style="margin-top: 12px; margin-left: 20px;">
                        <li>无 USB Dongle → 自动使用本地设备认证</li>
                        <li>Homed 平台登录成功</li>
                        <li>CBN 国网登录成功</li>
                        <li>首页数据加载正常</li>
                    </ol>
                    <div style="margin-top: 16px; padding: 12px; background: #f0fdf4; border-radius: 8px;">
                        <strong>相关案例:</strong> <code>case_002b_cbn_login_success_no_dongle.md</code>
                    </div>
                '''
            else:
                return '''
                    <p style="font-size: 16px;">该设备登录流程<strong style="color: var(--success);">完全正常</strong>：</p>
                    <ol style="margin-top: 12px; margin-left: 20px;">
                        <li>USB Dongle 正常识别</li>
                        <li>Homed 平台登录成功</li>
                        <li>CBN 国网登录成功</li>
                        <li>首页数据加载正常</li>
                    </ol>
                '''
    else:
        issues = []

        if is_linux:
            if not login_results['homed_login']:
                issues.append('<li>Web 登录页未检测到</li>')
            if not login_results['homed_user_list']:
                issues.append('<li>Homed API 未调用成功</li>')
            if not login_results['cbn_login']:
                issues.append('<li>用户数据未获取</li>')
            elif login_results['cbn_login']['status'] != 'success':
                issues.append('<li>用户数据获取失败</li>')

            return f'''
                <p style="font-size: 16px;">该 Linux STB 设备登录流程<strong style="color: var(--error);">存在问题</strong>：</p>
                <ol style="margin-top: 12px; margin-left: 20px;">
                    {"".join(issues)}
                    <li>请检查网络连接和 API 配置</li>
                </ol>
                <div style="margin-top: 16px; padding: 12px; background: #fef2f2; border-radius: 8px;">
                    <strong>平台:</strong> <code>Linux STB (iPanel 中间件)</code>
                </div>
            '''
        else:
            if not login_results['homed_login']:
                issues.append('<li>Homed 登录未检测到</li>')
            if not login_results['cbn_login']:
                issues.append('<li>CBN 登录未检测到</li>')
            elif login_results['cbn_login']['status'] != 'success':
                issues.append('<li>CBN 登录失败</li>')
            if not login_results['tabcards']:
                issues.append('<li>首页数据未获取</li>')

            return f'''
                <p style="font-size: 16px;">该设备登录流程<strong style="color: var(--error);">存在问题</strong>：</p>
                <ol style="margin-top: 12px; margin-left: 20px;">
                    {"".join(issues)}
                    <li>请参考相关案例文档进行排查</li>
                </ol>
                <div style="margin-top: 16px; padding: 12px; background: #fef2f2; border-radius: 8px;">
                    <strong>相关案例:</strong> <code>case_001_cbn_login_fail.md</code>
                </div>
            '''


def main():
    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <logfile> [output_path]")
        print("\n支持的平台:")
        print("  - Android TV logcat")
        print("  - Android STB ROM logcat")
        print("  - Linux STB")
        sys.exit(1)

    log_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = generate_html_report(log_path, output_path)
    if result:
        print(f"Report generated: {result}")


if __name__ == '__main__':
    main()
