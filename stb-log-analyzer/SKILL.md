---
name: stb-log-analyzer
description: |
  机顶盒 (STB) 日志分析技能。当用户说 "分析这个日志"、"分析 logs/xxx.log"、"检查登录情况"、"CBN 登录成功了吗"、"Homed 登录正常吗"、"检查栏目加载"、"哪些栏目加载了"、"生成报告"、"对比 a.log 和 b.log"、"看看有什么问题" 时使用此技能。支持 Android TV、Android STB ROM、Linux STB 三种平台，提供登录流程分析、模块故障诊断、CBN 栏目检测、HTML 报告生成。
---

# STB Log Analyzer - 技能定义

## 分析原则

1. **按需分析** - 根据用户请求只执行相关模块的检查
2. **节省 Token** - 不检索不必要的信息，精简输出
3. **报告可选** - HTML 报告仅在明确要求或全面分析时生成

---

## 模块化分析流程

### 第一步：意图识别

根据用户请求确定分析范围：

| 用户话术 | 分析模块 | 是否生成报告 |
|----------|----------|--------------|
| "分析日志" / "看看有什么问题" | 全部模块 | ✅ 是 |
| "检查登录情况" / "CBN 登录成功了吗" | homed + cbn | ❌ 否 |
| "检查栏目加载" / "哪些栏目加载了" | cbn_columns | ❌ 否 |
| "Dongle 状态怎么样" | dongle | ❌ 否 |
| "音频有问题吗" | audio | ❌ 否 |
| "网络正常吗" | network | ❌ 否 |
| "HDMI 有问题吗" | hdmi | ❌ 否 |
| "有崩溃吗" / "有 ANR 吗" | crash | ❌ 否 |
| "蓝牙正常吗" | bluetooth | ❌ 否 |
| "生成报告" / "生成网页版报告" | (基于上次分析或全部) | ✅ 是 |
| "对比 a.log 和 b.log" | 对比分析 | 视情况 |

### 第二步：执行对应脚本

```bash
# 按模块执行 (单一模块检查)
python scripts/pattern_matcher.py <logfile> --module cbn
python scripts/pattern_matcher.py <logfile> --module homed
python scripts/pattern_matcher.py <logfile> --module dongle
python scripts/pattern_matcher.py <logfile> --module bluetooth
python scripts/pattern_matcher.py <logfile> --module audio
python scripts/pattern_matcher.py <logfile> --module network
python scripts/pattern_matcher.py <logfile> --module hdmi

# 栏目检测 (专用脚本)
python scripts/cbn_columns_detector.py <logfile>

# 全面分析 (所有模块)
python scripts/pattern_matcher.py <logfile>

# 生成 HTML 报告 (仅在需要时)
python scripts/report_generator.py <logfile>
```

### 第三步：输出结果

- **单一模块检查**: 直接输出文本摘要，不生成 HTML
- **全面分析**: 输出摘要 + 生成 HTML 报告
- **用户要求报告**: 生成 HTML 报告

---

## 登录流程分析

当用户询问登录相关问题时执行：

```
1. Homed 平台登录 (前置条件)
   ├─ access.tsyrmt.cn/account/login (登录认证)
   └─ access.tsyrmt.cn/account/user/get_list (获取用户信息)
           ↓
2. CBN 国网登录 (核心业务)
   └─ GwSDK.initSDK → onLoginSuccess/onLoginError
```

| 状态 | Homed | CBN | 标志 |
|------|-------|-----|------|
| 完全成功 | `ret=0` | `onLoginSuccess` | 首页数据正常 |
| Homed 失败 | 无响应/错误 | - | 无 CBN 登录尝试 |
| CBN 失败 | 成功 | `onLoginError` 或无响应 | 需检查 loginParams |

---

## 模块速查表

| 模块 | 检查命令 | 关键日志标签 |
|------|----------|--------------|
| **homed** | `--module homed` | `ServiceHelper`, `StbApp` |
| **cbn** | `--module cbn` | `GwSDK`, `CBN_UI_SDK` |
| **cbn_columns** | `cbn_columns_detector.py` | `HomeDataManager`, `GwPortalFragment` |
| **dongle** | `--module dongle` | `DongleManager`, `DongleProtocol` |
| **bluetooth** | `--module bluetooth` | `BluetoothAdapter`, `audiohalservice` |
| **audio** | `--module audio` | `audio_hw_primary`, `AudioTrack` |
| **network** | `--module network` | `NET_SDK`, `NetworkSpeedMonitor` |
| **hdmi** | `--module hdmi` | `aml_hal_core_detect`, `tvhalServer` |
| **crash** | `--severity critical` | `ANR in`, `*** Build fingerprint` |

---

## 关键注意事项

1. **Dongle 与 CBN 登录无关** - 不接 Dongle 也可以成功登录 CBN
2. **Homed 是前置条件** - CBN 登录前必须先完成 Homed 平台登录
3. **时序很重要** - 按 PID 和时间戳关联事件
4. **平台差异** - Linux STB 使用 Web 登录页，Android 使用 SDK 登录

---

## 参考文件

需要详细领域知识时查阅：

| 目录 | 内容 |
|------|------|
| `references/modules/` | audio, network, hdmi, cbn_uisdk |
| `references/errors/` | crash_patterns, performance |
| `references/cases/` | case_001, case_002, case_002b |
| `references/platform/` | platform_diff |
| `scripts/config/` | keywords.yaml |
