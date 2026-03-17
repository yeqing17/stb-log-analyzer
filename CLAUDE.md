# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言偏好

**本项目使用中文进行所有交流和文档输出。**

## 项目概述

STB Log Analysis 是一个 Android 机顶盒 logcat 日志分析工具包。提供 Python 脚本用于解析 logcat 日志并匹配已知错误模式，附带各模块（音频、网络、HDMI、CBN SDK）的诊断参考文档。

## 运行脚本

```bash
# 解析 logcat 日志为结构化条目
python stb-log-analyzer/scripts/log_parser.py logs/yq1600cbn.log

# 匹配已知错误模式
python stb-log-analyzer/scripts/pattern_matcher.py logs/yq1600cbn.log

# 按模块过滤
python stb-log-analyzer/scripts/pattern_matcher.py logs/yq1600cbn.log --module cbn

# 按严重级别过滤
python stb-log-analyzer/scripts/pattern_matcher.py logs/yq1600cbn.log --severity critical
```

## 目录结构

```
F:\STBLogAnalysis\
├── logs/                          # 输入日志文件
├── stb-log-analyzer/
│   ├── scripts/
│   │   ├── log_parser.py          # 解析 logcat 为 LogEntry 数据类
│   │   ├── pattern_matcher.py     # 从配置匹配错误模式
│   │   └── config/keywords.yaml   # 模式定义（数据源）
│   ├── references/
│   │   ├── modules/               # 领域知识: audio.md, network.md, hdmi.md, cbn_uisdk.md
│   │   ├── errors/                # 错误模式: crash_patterns.md, performance.md
│   │   ├── cases/                 # 历史案例
│   │   └── keywords.md            # keywords.yaml 的 Markdown 副本，供 AI 参考
│   └── assets/report_template.md  # 分析报告模板
```

## 关键数据结构

- `LogEntry` (log_parser.py): `timestamp`, `level`, `tag`, `pid`, `message`, `raw`
- `Pattern` (pattern_matcher.py): `name`, `regex`, `severity`, `description`, `module`
- 模式配置 (keywords.yaml): 按模块分层 (cbn, hdmi, audio, network, crash, performance)

## 模式配置管理

模式定义在 `scripts/config/keywords.yaml`，这是数据源；`references/keywords.md` 是供人阅读的副本，需保持同步。

添加新模式:
1. 在 keywords.yaml 对应模块下添加
2. 同步更新 keywords.md
3. 用 pattern_matcher.py 测试

## 分析工作流

1. 从 Error (E) 和 Fatal (F) 级别条目入手
2. 匹配 keywords.yaml 中的已知模式
3. 领域特定问题查阅 `references/modules/`
4. 崩溃/ANR 查阅 `references/errors/crash_patterns.md`
5. 使用 `assets/report_template.md` 生成报告

## CBN SDK 登录流程

国网 (CBN) SDK 是常见问题来源:

1. **Homed 本地登录** → 获取基础 token
2. **GwSDK.initSDK** → 初始化 SDK
3. **GwSDK.login** → 认证
4. **获取 TabCards/pages** → 首页数据

典型故障链: USB Dongle 未识别 → `oid=null, caid=null` → 登录参数未解析 → 数据初始化失败

完整案例见 `references/cases/case_001_cbn_login_fail.md`。