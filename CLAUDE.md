# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言偏好

**本项目使用中文进行所有交流和文档输出。**

## 项目概述

STB Log Analysis 是一个机顶盒日志分析工具包，支持多种平台：

| 平台 | 说明 | 日志格式 |
|------|------|----------|
| **Android TV** | Android TV + homed APK | logcat 标准格式 |
| **Android STB ROM** | Android 机顶盒 ROM + homed APK | logcat 带 TID 格式 |
| **Linux STB** | Linux 机顶盒 + iPanel中间件 | 自定义格式 |

提供 Python 脚本用于解析日志并匹配已知错误模式，附带各模块（音频、网络、HDMI、CBN SDK）的诊断参考文档。

## 运行脚本

```bash
# 解析日志为结构化条目（自动检测平台）
python stb-log-analyzer/scripts/log_parser.py logs/android-stb-rom.log
python stb-log-analyzer/scripts/log_parser.py logs/linux-stb.log

# 匹配已知错误模式
python stb-log-analyzer/scripts/pattern_matcher.py logs/android-stb-rom.log

# 按模块过滤
python stb-log-analyzer/scripts/pattern_matcher.py logs/android-stb-rom.log --module cbn
python stb-log-analyzer/scripts/pattern_matcher.py logs/android-stb-rom.log --module selinux
python stb-log-analyzer/scripts/pattern_matcher.py logs/android-stb-rom.log --module hal

# 按严重级别过滤
python stb-log-analyzer/scripts/pattern_matcher.py logs/android-stb-rom.log --severity critical

# 按平台过滤
python stb-log-analyzer/scripts/pattern_matcher.py logs/android-stb-rom.log --platform android_stb_rom
```

## 目录结构

```
D:\Skillccc\stb-log-analyzer\
├── logs/                          # 输入日志文件
│   ├── android-stb-rom.log        # Android STB ROM 日志示例
│   └── linux-stb.log              # Linux STB 日志示例
├── stb-log-analyzer/
│   ├── scripts/
│   │   ├── log_parser.py          # 解析日志为 LogEntry 数据类
│   │   ├── pattern_matcher.py     # 从配置匹配错误模式
│   │   └── config/keywords.yaml   # 模式定义（数据源）
│   ├── references/
│   │   ├── modules/               # 领域知识: audio.md, network.md, hdmi.md, cbn_uisdk.md
│   │   ├── errors/                # 错误模式: crash_patterns.md, performance.md
│   │   ├── cases/                 # 历史案例
│   │   ├── platform/              # 平台差异: platform_diff.md
│   │   └── keywords.md            # keywords.yaml 的 Markdown 副本，供 AI 参考
│   └── assets/report_template.md  # 分析报告模板
```

## 关键数据结构

- `LogEntry` (log_parser.py): `timestamp`, `level`, `tag`, `pid`, `tid`, `message`, `raw`, `platform`
- `Pattern` (pattern_matcher.py): `name`, `regex`, `severity`, `description`, `module`, `platforms`
- `PlatformType` (枚举): `ANDROID_TV`, `ANDROID_STB_ROM`, `LINUX_STB`, `UNKNOWN`
- 模式配置 (keywords.yaml): 按模块分层，支持平台特定模式

## 平台差异

### Android TV vs Android STB ROM

| 特性 | Android TV | Android STB ROM |
|------|------------|-----------------|
| 格式 | `Level/Tag(PID):` | `PID TID Level Tag:` |
| TID | 无 | 有 |
| 特有模式 | 较少 | SELinux, HAL层 |

详见 `references/platform/platform_diff.md`

## 模式配置管理

模式定义在 `scripts/config/keywords.yaml`，这是数据源；`references/keywords.md` 是供人阅读的副本，需保持同步。

添加新模式:
1. 在 keywords.yaml 对应模块下添加
2. 可选设置 `platforms` 字段限制适用平台
3. 同步更新 keywords.md
4. 用 pattern_matcher.py 测试

## 分析工作流

1. 从 Error (E) 和 Fatal (F) 级别条目入手
2. 匹配 keywords.yaml 中的已知模式
3. 领域特定问题查阅 `references/modules/`
4. 崩溃/ANR 查阅 `references/errors/crash_patterns.md`
5. 平台差异查阅 `references/platform/platform_diff.md`
6. 使用 `assets/report_template.md` 生成报告

## CBN SDK 登录流程

国网 (CBN) SDK 是常见问题来源:

1. **Homed 本地登录** → 获取基础 token
2. **GwSDK.initSDK** → 初始化 SDK
3. **GwSDK.login** → 认证
4. **获取 TabCards/pages** → 首页数据

典型故障链: USB Dongle 未识别 → `oid=null, caid=null` → 登录参数未解析 → 数据初始化失败

完整案例见 `references/cases/case_001_cbn_login_fail.md`。