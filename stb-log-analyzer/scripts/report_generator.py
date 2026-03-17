#!/usr/bin/env python3
"""
STB Log Analyzer - HTML Report Generator
生成日志分析报告的 HTML 版本
"""

import os
import sys
import yaml
import re
from datetime import datetime
from pathlib import Path

def load_config():
    """加载 keywords.yaml 配置"""
    config_path = Path(__file__).parent / 'config' / 'keywords.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def parse_log_line(line):
    """解析 logcat 行"""
    pattern = r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+([VDIWEF])/([^\(]+)\(\s*(\d+)\):\s*(.*)$'
    match = re.match(pattern, line)
    if match:
        return {
            'timestamp': match.group(1),
            'level': match.group(2),
            'tag': match.group(3).strip(),
            'pid': match.group(4),
            'message': match.group(5)
        }
    return None

def analyze_login_flow(log_path):
    """分析登录流程"""
    results = {
        'homed_login': None,
        'homed_user_list': None,
        'cbn_init': None,
        'cbn_login': None,
        'dongle_status': None,
        'device_auth': None,
        'tabcards': [],
        'device_info': {}
    }

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            # account/login
            if 'account/login' in line and 'response' in line:
                parsed = parse_log_line(line)
                results['homed_login'] = {
                    'status': 'success',
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                }

            # user/get_list
            if 'user/get_list' in line and 'response' in line:
                parsed = parse_log_line(line)
                results['homed_user_list'] = {
                    'status': 'success',
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                }

            # GwSDK initSDK
            match = re.search(r'GwSDK.*initSDK env\s*=\s*(\w+).*province\s*=\s*(\w+)', line)
            if match:
                parsed = parse_log_line(line)
                results['cbn_init'] = {
                    'status': 'success',
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                }
                results['device_info']['env'] = match.group(1)
                results['device_info']['province'] = match.group(2)

            # onLoginSuccess
            if 'onLoginSuccess' in line:
                parsed = parse_log_line(line)
                results['cbn_login'] = {
                    'status': 'success',
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                }

            # onLoginError
            if 'onLoginError' in line:
                parsed = parse_log_line(line)
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
                parsed = parse_log_line(line)
                results['tabcards'].append({
                    'size': int(match.group(1)),
                    'time': parsed['timestamp'] if parsed else 'Unknown',
                    'line': line_num
                })

    return results

def generate_html_report(log_path, output_path=None):
    """生成 HTML 报告"""
    log_path = Path(log_path)
    if not log_path.exists():
        print(f"Error: Log file not found: {log_path}")
        return None

    # 分析日志
    login_results = analyze_login_flow(log_path)

    # 确定整体状态
    all_success = (
        login_results['homed_login'] and
        login_results['cbn_login'] and
        login_results['cbn_login']['status'] == 'success' and
        len(login_results['tabcards']) > 0
    )

    summary_color = 'success' if all_success else 'error'
    summary_icon = '✓' if all_success else '✗'
    summary_text = '登录状态: 全部成功' if all_success else '登录状态: 存在问题'

    # 生成流程图
    flow_steps = []

    # Dongle
    if login_results['dongle_status'] == 'none':
        flow_steps.append('<div class="flow-step">USB Dongle<br><small style="color: var(--error);">❌ 无设备</small></div>')
    elif login_results['dongle_status'] == 'connected':
        flow_steps.append('<div class="flow-step success">USB Dongle<br><small style="color: var(--success);">✓ 已连接</small></div>')
    else:
        flow_steps.append('<div class="flow-step">USB Dongle<br><small>未检测</small></div>')

    flow_steps.append('<span class="flow-arrow">→</span>')

    # 认证方式
    if login_results['device_auth'] == 'local':
        flow_steps.append('<div class="flow-step success">本地认证<br><small style="color: var(--success);">✓ 本地设备ID</small></div>')
    elif login_results['device_auth'] == 'dongle':
        flow_steps.append('<div class="flow-step success">Dongle认证<br><small style="color: var(--success);">✓ deviceAuth</small></div>')
    else:
        flow_steps.append('<div class="flow-step">认证方式<br><small>未检测</small></div>')

    flow_steps.append('<span class="flow-arrow">→</span>')

    # Homed
    if login_results['homed_login']:
        flow_steps.append('<div class="flow-step success">Homed 登录<br><small style="color: var(--success);">✓ 成功</small></div>')
    else:
        flow_steps.append('<div class="flow-step">Homed 登录<br><small>未检测</small></div>')

    flow_steps.append('<span class="flow-arrow">→</span>')

    # CBN
    if login_results['cbn_login'] and login_results['cbn_login']['status'] == 'success':
        flow_steps.append('<div class="flow-step success">CBN 登录<br><small style="color: var(--success);">✓ onLoginSuccess</small></div>')
    elif login_results['cbn_login']:
        flow_steps.append('<div class="flow-step">CBN 登录<br><small style="color: var(--error);">✗ onLoginError</small></div>')
    else:
        flow_steps.append('<div class="flow-step">CBN 登录<br><small>未检测</small></div>')

    flow_steps.append('<span class="flow-arrow">→</span>')

    # 首页数据
    if login_results['tabcards']:
        flow_steps.append(f'<div class="flow-step success">首页数据<br><small style="color: var(--success);">✓ {len(login_results["tabcards"])}次</small></div>')
    else:
        flow_steps.append('<div class="flow-step">首页数据<br><small>未获取</small></div>')

    # 生成登录表格行
    login_rows = []

    # Dongle
    if login_results['dongle_status'] == 'none':
        login_rows.append('<tr><td>USB Dongle</td><td><span class="status-badge error">❌ 无设备</span></td><td><code>usb.idongle.alive = []</code></td><td>无 Dongle，使用本地认证</td></tr>')
    elif login_results['dongle_status'] == 'connected':
        login_rows.append('<tr><td>USB Dongle</td><td><span class="status-badge success">✓ 已连接</span></td><td><code>usb.idongle.alive</code></td><td>Dongle 已识别</td></tr>')
    else:
        login_rows.append('<tr><td>USB Dongle</td><td><span class="status-badge info">未检测</span></td><td>-</td><td>-</td></tr>')

    # 认证方式
    if login_results['device_auth'] == 'local':
        login_rows.append('<tr><td>设备认证</td><td><span class="status-badge success">✓ 成功</span></td><td><code>deviceAuthByLocalDevice</code></td><td>本地设备认证</td></tr>')
    elif login_results['device_auth'] == 'dongle':
        login_rows.append('<tr><td>设备认证</td><td><span class="status-badge success">✓ 成功</span></td><td><code>deviceAuth true</code></td><td>Dongle 认证</td></tr>')
    else:
        login_rows.append('<tr><td>设备认证</td><td><span class="status-badge info">未检测</span></td><td>-</td><td>-</td></tr>')

    # Homed 登录
    if login_results['homed_login']:
        login_rows.append(f'<tr><td>Homed 登录</td><td><span class="status-badge success">✓ 成功</span></td><td><code>account/login</code></td><td>{login_results["homed_login"]["time"]}</td></tr>')
    else:
        login_rows.append('<tr><td>Homed 登录</td><td><span class="status-badge error">✗ 未检测到</span></td><td>-</td><td>-</td></tr>')

    # CBN 初始化
    if login_results['cbn_init']:
        env = login_results['device_info'].get('env', '-')
        province = login_results['device_info'].get('province', '-')
        login_rows.append(f'<tr><td>CBN 初始化</td><td><span class="status-badge success">✓ 成功</span></td><td><code>GwSDK.initSDK</code></td><td>{env}, {province}</td></tr>')
    else:
        login_rows.append('<tr><td>CBN 初始化</td><td><span class="status-badge info">未检测</span></td><td>-</td><td>-</td></tr>')

    # CBN 登录
    if login_results['cbn_login'] and login_results['cbn_login']['status'] == 'success':
        login_rows.append(f'<tr><td>CBN 登录</td><td><span class="status-badge success">✓ 成功</span></td><td><code>onLoginSuccess</code></td><td>{login_results["cbn_login"]["time"]}</td></tr>')
    elif login_results['cbn_login']:
        login_rows.append(f'<tr><td>CBN 登录</td><td><span class="status-badge error">✗ 失败</span></td><td><code>onLoginError</code></td><td>{login_results["cbn_login"]["time"]}</td></tr>')
    else:
        login_rows.append('<tr><td>CBN 登录</td><td><span class="status-badge error">✗ 未检测到</span></td><td>-</td><td>-</td></tr>')

    # 首页数据
    if login_results['tabcards']:
        sizes = [str(t['size']) for t in login_results['tabcards']]
        tabcards_text = f"多次获取 ({'/'.join(sizes[:3])}条)"
        login_rows.append(f'<tr><td>首页数据</td><td><span class="status-badge success">✓ 成功</span></td><td><code>onGetTabCards</code></td><td>{tabcards_text}</td></tr>')
    else:
        login_rows.append('<tr><td>首页数据</td><td><span class="status-badge error">✗ 未获取</span></td><td>-</td><td>-</td></tr>')

    # 生成时序
    timeline_items = []

    if login_results['dongle_status'] == 'none':
        timeline_items.append('<div class="timeline-item error"><span class="timeline-time">--</span><span class="timeline-event">Dongle 检查: 无设备</span><span class="timeline-stage">Dongle</span></div>')
    elif login_results['dongle_status'] == 'connected':
        timeline_items.append('<div class="timeline-item success"><span class="timeline-time">--</span><span class="timeline-event">Dongle 检查: 已连接</span><span class="timeline-stage">Dongle</span></div>')

    if login_results['device_auth'] == 'local':
        timeline_items.append('<div class="timeline-item success"><span class="timeline-time">--</span><span class="timeline-event">切换本地设备认证</span><span class="timeline-stage">认证</span></div>')

    if login_results['homed_login']:
        timeline_items.append(f'<div class="timeline-item success"><span class="timeline-time">{login_results["homed_login"]["time"]}</span><span class="timeline-event">Homed 登录成功</span><span class="timeline-stage">Homed</span></div>')

    if login_results['cbn_init']:
        timeline_items.append(f'<div class="timeline-item"><span class="timeline-time">{login_results["cbn_init"]["time"]}</span><span class="timeline-event">GwSDK.initSDK 开始</span><span class="timeline-stage">CBN</span></div>')

    if login_results['cbn_login']:
        status_class = 'success' if login_results['cbn_login']['status'] == 'success' else 'error'
        status_text = '成功' if login_results['cbn_login']['status'] == 'success' else '失败'
        timeline_items.append(f'<div class="timeline-item {status_class}"><span class="timeline-time">{login_results["cbn_login"]["time"]}</span><span class="timeline-event"><strong>{"onLoginSuccess" if login_results["cbn_login"]["status"] == "success" else "onLoginError"}</strong></span><span class="timeline-stage">CBN {status_text}</span></div>')

    for tc in login_results['tabcards'][:3]:
        timeline_items.append(f'<div class="timeline-item success"><span class="timeline-time">{tc["time"]}</span><span class="timeline-event">onGetTabCards list.size:{tc["size"]}</span><span class="timeline-stage">数据加载</span></div>')

    # 生成结论
    if all_success:
        if login_results['dongle_status'] == 'none':
            conclusion = '''
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
            conclusion = '''
                <p style="font-size: 16px;">该设备登录流程<strong style="color: var(--success);">完全正常</strong>：</p>
                <ol style="margin-top: 12px; margin-left: 20px;">
                    <li>USB Dongle 正常识别</li>
                    <li>Homed 平台登录成功</li>
                    <li>CBN 国网登录成功</li>
                    <li>首页数据加载正常</li>
                </ol>
            '''
    else:
        conclusion = '''
            <p style="font-size: 16px;">该设备登录流程<strong style="color: var(--error);">存在问题</strong>：</p>
            <ol style="margin-top: 12px; margin-left: 20px;">
                <li>请检查上述失败项</li>
                <li>参考相关案例文档进行排查</li>
            </ol>
        '''

    # 读取模板
    template_path = Path(__file__).parent.parent / 'assets' / 'report_template.html'
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # 设备信息
    device_info = f"{login_results['device_info'].get('province', 'Unknown')} / {login_results['device_info'].get('env', 'Unknown')}"
    device_id = login_results['device_info'].get('oid', 'Unknown')

    # 替换占位符
    html_content = template.replace('{{log_file}}', log_path.name)
    html_content = html_content.replace('{{device_info}}', device_info)
    html_content = html_content.replace('{{device_id}}', device_id)
    html_content = html_content.replace('{{analysis_time}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    html_content = html_content.replace('{{summary_color}}', summary_color)
    html_content = html_content.replace('{{summary_icon}}', summary_icon)
    html_content = html_content.replace('{{summary_text}}', summary_text)
    html_content = html_content.replace('{{flow_diagram}}', '\n'.join(flow_steps))
    html_content = html_content.replace('{{login_rows}}', '\n'.join(login_rows))
    html_content = html_content.replace('{{timeline_items}}', '\n'.join(timeline_items))
    html_content = html_content.replace('{{conclusion}}', conclusion)

    # 输出路径
    if output_path is None:
        reports_dir = Path(__file__).parent.parent.parent / 'reports'
        reports_dir.mkdir(exist_ok=True)
        output_path = reports_dir / f"{log_path.stem}_report.html"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_path

def main():
    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <logfile> [output_path]")
        sys.exit(1)

    log_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = generate_html_report(log_path, output_path)
    if result:
        print(f"Report generated: {result}")

if __name__ == '__main__':
    main()
