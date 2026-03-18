#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CBN 栏目加载检测器
用于分析日志中加载了哪些国网栏目，显示 Tab ID、名称、数据来源等信息

用法:
    python cbn_columns_detector.py <logfile>
"""

import re
import sys
import io
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# 设置 stdout 编码为 UTF-8 (Windows 兼容)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


@dataclass
class ColumnInfo:
    """栏目信息"""
    tab_id: str
    card_count: Optional[int] = None
    source: str = "unknown"  # cache, api
    timestamp: Optional[str] = None
    line_number: int = 0


@dataclass
class HomedLabelInfo:
    """Homed Label 信息"""
    label_id: str
    label_name: str = ""
    has_data: bool = False
    timestamp: Optional[str] = None
    line_number: int = 0


class CBNColumnsDetector:
    """CBN 栏目检测器"""

    # CBN SDK 栏目模式
    CBN_PATTERNS = {
        'cache_load': re.compile(r'读取缓存的page\s+(\S+)\s+成功'),
        'use_cache': re.compile(r'使用本地缓存:\s*(\S+)'),
        'tabcards': re.compile(r'onGetTabCards list\.size:(\d+)'),
        'tab_switch': re.compile(r'setUserVisibleHint isVisibleToUser = true.*tabId\s*=\s*(\S+)'),
        'tab_resume': re.compile(r'HomeContentFragment onResume.*tabId\s*:\s*(\S+)'),
        'fragment_create': re.compile(r'createFragment.*es_tabId=(\S+)&'),
    }

    # Homed Label 模式
    HOMED_PATTERNS = {
        'label_request': re.compile(r'label=(\d+)'),
        'label_name': re.compile(r'entry\s*=\s*name\s*=\s*(\S+).*id[=:](\d+)'),
        'patchwall_response': re.compile(r'patchwall onResponse.*name\s*=\s*(\S+).*id[=:](\d+)'),
        'empty_data': re.compile(r'"type_list"\s*:\s*\[\]'),
        'empty_result': re.compile(r'updatePatchWallData end.*total=0.*adapterCount=0.*name\s*=\s*(\S+).*id[=:](\d+)'),
        'get_list_url': re.compile(r'patchwall/get_list[^"]*label=(\d+)'),
        'response_json': re.compile(r'ServiceHelper:.*"ret":\s*(\d+)'),
    }

    def __init__(self, logfile: str):
        self.logfile = Path(logfile)
        self.cbn_columns: dict[str, ColumnInfo] = {}
        self.homed_labels: dict[str, HomedLabelInfo] = {}
        self.current_tab_id: Optional[str] = None
        self.tab_name_map: dict[str, str] = {}  # tab_id -> name mapping
        self.pending_label: Optional[str] = None  # 当前请求的 label

    def detect(self) -> tuple[dict[str, ColumnInfo], dict[str, HomedLabelInfo]]:
        """检测日志中的栏目加载情况"""
        with open(self.logfile, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                self._process_line(line, line_num)

        return self.cbn_columns, self.homed_labels

    def _process_line(self, line: str, line_num: int):
        """处理单行日志"""
        # 提取时间戳
        timestamp = self._extract_timestamp(line)

        # CBN SDK 栏目检测 - 只匹配第一个
        for pattern_name, pattern in self.CBN_PATTERNS.items():
            match = pattern.search(line)
            if match:
                self._process_cbn_match(pattern_name, match, line_num, timestamp)
                break

        # Homed Label 检测 - 需要检测多个模式
        for pattern_name, pattern in self.HOMED_PATTERNS.items():
            match = pattern.search(line)
            if match:
                self._process_homed_match(pattern_name, match, line, line_num, timestamp)

    def _extract_timestamp(self, line: str) -> Optional[str]:
        """提取时间戳"""
        # Android STB ROM 格式: 03-18 11:38:50.123
        match = re.search(r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
        return match.group(1) if match else None

    def _process_cbn_match(self, pattern_name: str, match, line_num: int, timestamp: Optional[str]):
        """处理 CBN 栏目匹配"""
        tab_id = match.group(1).rstrip(',')

        if pattern_name == 'cache_load':
            if tab_id not in self.cbn_columns:
                self.cbn_columns[tab_id] = ColumnInfo(tab_id=tab_id)
            self.cbn_columns[tab_id].source = "cache"
            self.cbn_columns[tab_id].timestamp = timestamp
            self.cbn_columns[tab_id].line_number = line_num
            self.current_tab_id = tab_id

        elif pattern_name == 'use_cache':
            if tab_id not in self.cbn_columns:
                self.cbn_columns[tab_id] = ColumnInfo(tab_id=tab_id)
            self.cbn_columns[tab_id].source = "cache"
            self.current_tab_id = tab_id

        elif pattern_name == 'tabcards':
            count = int(tab_id)  # 这里 tab_id 实际是数量
            if self.current_tab_id and self.current_tab_id in self.cbn_columns:
                self.cbn_columns[self.current_tab_id].card_count = count

        elif pattern_name in ('tab_switch', 'tab_resume'):
            if tab_id not in self.cbn_columns:
                self.cbn_columns[tab_id] = ColumnInfo(tab_id=tab_id)
            self.current_tab_id = tab_id

    def _process_homed_match(self, pattern_name: str, match, line: str, line_num: int, timestamp: Optional[str]):
        """处理 Homed Label 匹配"""
        if pattern_name == 'label_name':
            name = match.group(1)
            label_id = match.group(2)
            self.tab_name_map[label_id] = name

        elif pattern_name == 'label_request':
            label_id = match.group(1)
            if label_id not in self.homed_labels:
                self.homed_labels[label_id] = HomedLabelInfo(label_id=label_id)
            self.homed_labels[label_id].timestamp = timestamp
            self.homed_labels[label_id].line_number = line_num
            # 尝试获取名称
            if label_id in self.tab_name_map:
                self.homed_labels[label_id].label_name = self.tab_name_map[label_id]

        elif pattern_name == 'get_list_url':
            # 记录当前请求的 label
            self.pending_label = match.group(1)

        elif pattern_name == 'patchwall_response':
            name = match.group(1)
            label_id = match.group(2)
            if label_id not in self.homed_labels:
                self.homed_labels[label_id] = HomedLabelInfo(label_id=label_id)
            self.homed_labels[label_id].label_name = name
            # 先假设有数据，后续 empty_data 会修正
            self.homed_labels[label_id].has_data = True

        elif pattern_name == 'empty_data':
            # 检查最近的 label 请求
            if self.pending_label and self.pending_label in self.homed_labels:
                self.homed_labels[self.pending_label].has_data = False

        elif pattern_name == 'empty_result':
            # 直接从结果行提取 label 信息
            name = match.group(1)
            label_id = match.group(2)
            if label_id in self.homed_labels:
                self.homed_labels[label_id].label_name = name
                self.homed_labels[label_id].has_data = False

    def print_report(self):
        """打印栏目加载报告"""
        self.detect()

        print("=" * 60)
        print("CBN SDK 栏目加载报告")
        print("=" * 60)

        if self.cbn_columns:
            print("\n【国网 SDK 栏目 (CBN_UI_SDK)】")
            print("-" * 60)
            print(f"{'Tab ID':<20} {'卡片数':<10} {'数据来源':<10} {'时间'}")
            print("-" * 60)

            for tab_id, info in self.cbn_columns.items():
                count = str(info.card_count) if info.card_count else "-"
                source = "本地缓存" if info.source == "cache" else "API"
                ts = info.timestamp or "-"
                print(f"{tab_id:<20} {count:<10} {source:<10} {ts}")

        if self.homed_labels:
            print("\n【Homed Label 栏目】")
            print("-" * 60)
            print(f"{'Label ID':<12} {'名称':<15} {'数据状态':<10} {'时间'}")
            print("-" * 60)

            for label_id, info in self.homed_labels.items():
                name = info.label_name or "-"
                status = "有数据" if info.has_data else "空数据"
                ts = info.timestamp or "-"
                print(f"{label_id:<12} {name:<15} {status:<10} {ts}")

        # 统计汇总
        print("\n" + "=" * 60)
        print("汇总统计")
        print("=" * 60)
        print(f"CBN SDK 栏目数: {len(self.cbn_columns)}")
        print(f"Homed Label 数: {len(self.homed_labels)}")

        # 检查空数据
        empty_labels = [info for info in self.homed_labels.values() if not info.has_data]
        if empty_labels:
            print(f"\n[!] 空数据 Label: {len(empty_labels)} 个")
            for info in empty_labels:
                print(f"   - Label {info.label_id}: {info.label_name or '未知'}")


def main():
    if len(sys.argv) < 2:
        print("用法: python cbn_columns_detector.py <logfile>")
        print("\n示例:")
        print("  python cbn_columns_detector.py logs/weixin-log.log")
        sys.exit(1)

    logfile = sys.argv[1]
    if not Path(logfile).exists():
        print(f"错误: 文件不存在 - {logfile}")
        sys.exit(1)

    detector = CBNColumnsDetector(logfile)
    detector.print_report()


if __name__ == "__main__":
    main()
