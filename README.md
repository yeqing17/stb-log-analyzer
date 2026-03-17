# STB Log Analyzer

机顶盒日志分析工具，支持 Android 和 Linux 平台，用于诊断登录流程、模块故障等问题。

## 支持平台

| 平台 | 说明 | 日志格式 |
|------|------|----------|
| **Android TV** | Android TV + homed APK | logcat 标准格式 |
| **Android STB ROM** | Android 机顶盒 ROM + homed APK | logcat 带 TID 格式 |
| **Linux STB** | Linux 机顶盒 + iPanel 中间件 | 自定义格式 |

---

## 快速开始

### 触发话术

| 话术 | 说明 |
|------|------|
| `分析这个日志` / `分析 logs/xxx.log` | 完整分析 |
| `检查登录情况` | 检查 Homed + CBN 登录状态 |
| `CBN 登录成功了吗` | 重点检查 CBN 登录 |
| `对比 a.log 和 b.log` | 对比两个日志差异 |
| `生成网页版报告` | 生成 HTML 报告 |

### 示例

```
用户: 分析一下 logs/yqtest1.log 的登录情况

AI: [自动运行分析脚本，生成诊断报告]
```

---

## 登录流程

### Android 平台

```
┌─────────────────────────────────────────────┐
│  1. Homed 平台登录 (前置条件)               │
│     └─ account/login → ret=0               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  2. CBN 国网登录 (核心业务)                 │
│     └─ GwSDK.login → onLoginSuccess        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  3. 首页数据加载                            │
│     └─ onGetTabCards list.size:N           │
└─────────────────────────────────────────────┘
```

### Linux STB 平台

```
┌─────────────────────────────────────────────┐
│  1. Web 登录页加载                          │
│     └─ login.php                           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  2. Homed API 调用                          │
│     └─ account/user/get_list → home_id     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  3. 用户数据获取                            │
│     └─ nick_name, device_id                │
└─────────────────────────────────────────────┘
```

### 判断标准

| 阶段 | 成功标志 | 失败标志 |
|------|----------|----------|
| Homed | `account/login` 响应 + `ret=0` | 无响应 / `ret≠0` |
| CBN | `onLoginSuccess` | `onLoginError` 或无回调 |
| 首页 | `onGetTabCards list.size:N` (N>0) | `onGetTabCardsError` |

---

## 常用命令

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

# 生成 HTML 报告
python stb-log-analyzer/scripts/report_generator.py logs/xxx.log
```

---

## 目录结构

```
STBLogAnalysis/
├── logs/                           # 日志文件存放
├── reports/                        # 生成的 HTML 报告
├── stb-log-analyzer/
│   ├── SKILL.md                    # 技能定义 (AI 参考)
│   ├── scripts/
│   │   ├── pattern_matcher.py      # 模式匹配脚本
│   │   ├── report_generator.py     # 报告生成脚本
│   │   └── config/keywords.yaml    # 模式配置
│   ├── references/
│   │   ├── modules/                # 模块知识库
│   │   ├── cases/                  # 历史案例
│   │   └── keywords.md             # 关键词参考
│   └── assets/
│       └── report_template.html    # 报告模板
└── README.md                       # 本文件
```

---

## 触发话术速查表

### 完整分析
| 话术 | 说明 |
|------|------|
| `分析这个日志` | 完整分析当前日志 |
| `分析 logs/xxx.log` | 分析指定文件 |
| `看看有什么问题` | 问题诊断 |

### 登录流程
| 话术 | 说明 |
|------|------|
| `检查登录情况` | Homed + CBN 状态 |
| `CBN 登录成功了吗` | CBN 登录检查 |
| `国网登录有问题吗` | CBN 问题诊断 |
| `Homed 登录正常吗` | Homed 检查 |

### 模块检查
| 话术 | 模块 |
|------|------|
| `Dongle 状态怎么样` | USB Dongle |
| `音频有问题吗` | Audio |
| `网络正常吗` | Network |
| `HDMI 有问题吗` | HDMI |
| `有崩溃吗` / `有 ANR 吗` | Crash |

### 对比分析
| 话术 | 说明 |
|------|------|
| `对比 a.log 和 b.log` | 对比两个日志 |
| `和成功的日志有什么区别` | 差异分析 |
| `找出失败原因` | 问题定位 |

### 生成报告
| 话术 | 说明 |
|------|------|
| `生成报告` | 生成 HTML 报告 |
| `生成网页版报告` | 同上 |
| `导出分析报告` | 同上 |

---

## 注意事项

1. **Dongle 与 CBN 登录无关** - 不接 Dongle 也可以成功登录 CBN
2. **Homed 是前置条件** - CBN 登录前必须先完成 Homed 平台登录
3. **时序很重要** - 按 PID 和时间戳关联事件
4. **平台差异** - Linux STB 使用 Web 登录页，Android 使用 SDK 登录
5. **自动检测** - 工具会自动检测日志平台类型并应用对应的分析规则

---

## 相关案例

| 案例 | 说明 |
|------|------|
| `case_001_cbn_login_fail.md` | CBN 登录失败 (Dongle 问题) |
| `case_002_cbn_login_success.md` | CBN 登录成功 (有 Dongle) |
| `case_002b_cbn_login_success_no_dongle.md` | CBN 登录成功 (无 Dongle) |
