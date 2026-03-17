---
name: stb-log-analyzer
description: |
  机顶盒 (STB) 日志分析技能。分析 Android 和 Linux 机顶盒日志，识别问题、分类故障并提供诊断建议。

  支持平台:
  - Android TV (logcat 标准格式)
  - Android STB ROM (logcat 带 TID 格式)
  - Linux STB (iPanel 中间件)

  核心能力:
  - 登录流程分析 (Homed + CBN)
  - 模块故障诊断 (蓝牙、音频、网络、HDMI 等)
  - 模式匹配与错误检测
  - 生成 HTML 分析报告
---

# STB Log Analyzer - 技能定义

## 分析流程

```
┌─────────────────────────────────────────────────────────┐
│  1. 确认日志文件                                         │
│     └─ 用户指定 或 默认 logs/ 目录                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  2. 平台识别                                             │
│     ├─ Android TV logcat (标准格式)                      │
│     ├─ Android STB ROM logcat (带TID格式)               │
│     └─ Linux STB (iPanel 中间件)                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  3. 运行模式匹配                                         │
│     └─ python scripts/pattern_matcher.py <logfile>      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  4. 分析匹配结果                                         │
│     ├─ Critical/Error: 优先处理                          │
│     ├─ Warning: 选择性处理                               │
│     └─ Info: 参考信息                                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  5. 领域知识查阅                                         │
│     ├─ 模块问题 → references/modules/                   │
│     ├─ 崩溃/ANR → references/errors/                    │
│     └─ 历史案例 → references/cases/                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  6. 生成分析报告 (可选)                                  │
│     └─ python scripts/report_generator.py <logfile>     │
└─────────────────────────────────────────────────────────┘
```

---

## 登录流程分析

### 流程架构

```
1. Homed 平台登录 (前置条件)
   ├─ access.tsyrmt.cn/account/login (登录认证)
   └─ access.tsyrmt.cn/account/user/get_list (获取用户信息)
           ↓
2. CBN 国网登录 (核心业务)
   └─ GwSDK.initSDK → onLoginSuccess/onLoginError
```

### 判断标准

| 状态 | Homed | CBN | 标志 |
|------|-------|-----|------|
| 完全成功 | `ret=0` | `onLoginSuccess` | 首页数据正常 |
| Homed 失败 | 无响应/错误 | - | 无 CBN 登录尝试 |
| CBN 失败 | 成功 | `onLoginError` 或无响应 | 需检查 loginParams |

**参考文档:** `references/modules/cbn_uisdk.md`

---

## 模块对照表

| 模块 | 关键日志标签 | 参考文档 |
|------|--------------|----------|
| **Homed** | `ServiceHelper`, `StbApp` | `modules/cbn_uisdk.md` |
| **CBN** | `GwSDK`, `CBN_UI_SDK`, `CBN-sdk` | `modules/cbn_uisdk.md` |
| **Dongle** | `DongleManager`, `DongleProtocol` | `modules/cbn_uisdk.md` |
| **Audio** | `audio_hw_primary`, `AudioTrack` | `modules/audio.md` |
| **Network** | `NET_SDK`, `NetworkSpeedMonitor` | `modules/network.md` |
| **HDMI** | `aml_hal_core_detect`, `tvhalServer` | `modules/hdmi.md` |
| **Bluetooth** | `BluetoothAdapter`, `audiohalservice` | `keywords.yaml` |
| **SELinux** | `avc: denied`, `SELinux` | `keywords.yaml` |
| **HAL** | `HwcFbFreshfbHandle`, `HWComposer` | `keywords.yaml` |
| **Crash** | `ANR in`, `*** Build fingerprint` | `errors/crash_patterns.md` |
| **Linux STB** | `[tm=XXX][tid:XXX]`, `iPanel` | `platform/platform_diff.md` |

---

## 分析工具

### 模式匹配脚本

```bash
# 完整分析
python stb-log-analyzer/scripts/pattern_matcher.py logs/xxx.log

# 按模块过滤
python stb-log-analyzer/scripts/pattern_matcher.py logs/xxx.log --module cbn
python stb-log-analyzer/scripts/pattern_matcher.py logs/xxx.log --module homed
python stb-log-analyzer/scripts/pattern_matcher.py logs/xxx.log --module dongle
python stb-log-analyzer/scripts/pattern_matcher.py logs/xxx.log --module bluetooth

# 按平台过滤
python stb-log-analyzer/scripts/pattern_matcher.py logs/xxx.log --platform android_stb_rom
python stb-log-analyzer/scripts/pattern_matcher.py logs/xxx.log --platform linux_stb

# 按严重级别过滤
python stb-log-analyzer/scripts/pattern_matcher.py logs/xxx.log --severity critical
python stb-log-analyzer/scripts/pattern_matcher.py logs/xxx.log --severity error
```

### 报告生成脚本

```bash
# 生成 HTML 报告
python stb-log-analyzer/scripts/report_generator.py logs/xxx.log

# 指定输出路径
python stb-log-analyzer/scripts/report_generator.py logs/xxx.log reports/custom.html
```

### 手动 Grep 命令

```bash
# CBN 登录状态
grep -E "onLoginSuccess|onLoginError" <logfile>

# Homed 登录状态
grep -E "account/login|user/get_list|monitorAPIResponse.*success" <logfile>

# Dongle 状态
grep -E "deviceAuth|oid=.*caid=" <logfile>

# 崩溃/ANR
grep -E "ANR in|*** Build fingerprint|FATAL EXCEPTION" <logfile>
```

---

## 报告模板

分析完成后，使用以下结构生成报告：

```markdown
# 日志分析报告

**文件:** [filename.log]
**设备:** [从日志提取]
**分析时间:** YYYY-MM-DD HH:MM

## 摘要

[一句话描述主要问题]

## 登录流程检查

| 阶段 | 状态 | 详情 |
|------|------|------|
| Homed 登录 | ✅/❌ | ... |
| CBN 登录 | ✅/❌ | ... |
| 首页数据 | ✅/❌ | ... |

## 发现的问题

### 1. [问题名称] (Critical/Error)

**日志位置:** L[行号]
**模式匹配:** [pattern_name]
**日志片段:**
```
[相关日志]
```

**分析:** [问题原因分析]
**建议:** [修复建议]

## 相关案例

- [案例链接]
```

---

## 案例索引

| 案例 | 类型 | 文件 |
|------|------|------|
| CBN 登录失败 (Dongle 问题) | 失败 | `cases/case_001_cbn_login_fail.md` |
| CBN 登录成功 (有 Dongle) | 成功 | `cases/case_002_cbn_login_success.md` |
| CBN 登录成功 (无 Dongle) | 成功 | `cases/case_002b_cbn_login_success_no_dongle.md` |

---

## 关键注意事项

1. **Dongle 与 CBN 登录无关** - 不接 Dongle 也可以成功登录 CBN
2. **Homed 是前置条件** - CBN 登录前必须先完成 Homed 平台登录
3. **时序很重要** - 按 PID 和时间戳关联事件
4. **多 PID 关联** - 不同 PID 的日志可能相关（如 2964 后台 vs 9378 前台）
5. **平台差异** - Linux STB 使用 Web 登录页，Android 使用 SDK 登录
6. **自动检测** - 工具会自动检测日志平台类型并应用对应的分析规则
