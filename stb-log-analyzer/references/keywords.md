# Search Keywords / 搜索关键词

> **同步说明**: 本文件与 `scripts/config/keywords.yaml` 保持同步
> - yaml 版本：供脚本程序加载使用
> - md 版本：供 AI 直接阅读参考

日志分析常用搜索关键词，按模块和问题分类。

---

## 登录流程架构

```
┌─────────────────────────────────────────────────────────┐
│  1. Homed 平台登录 (前置条件)                             │
│     └─ access.tsyrmt.cn/account/user/get_list           │
│        └─ ret=0 表示成功                                 │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  2. CBN 国网登录 (核心业务)                               │
│     └─ GwSDK.login → onLoginSuccess                     │
└─────────────────────────────────────────────────────────┘
```

---

## Homed 平台登录 (前置条件)

### 关键日志标签

| 标签 | 含义 |
|------|------|
| `ServiceHelper` | Homed API 请求 |
| `HomedDataSourceManager` | 数据源管理 |
| `StbApp` | 应用主类 |

### 登录接口

| 接口 | 用途 |
|------|------|
| `access.tsyrmt.cn/account/login` | **登录认证** (核心) |
| `access.tsyrmt.cn/account/user/get_list` | 获取用户列表 |

### 成功模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `ServiceHelper.*response.*account/login` | Info | Homed 登录响应 |
| `ServiceHelper.*response.*user/get_list` | Info | Homed 用户列表获取 |
| `monitorAPIResponse onResponse success=true` | Info | API 响应成功 |

### 失败模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `not login.*skp` | Warning | Homed 未登录 |

### 诊断命令

```bash
# 检查 Homed 登录状态
grep -E "account/login|user/get_list|monitorAPIResponse.*success" <logfile>
```

---

## CBN / 国网 SDK

> **重要**: USB Dongle 与 CBN 登录是独立的两个模块。不接 Dongle 也可以成功登录 CBN。

### 关键日志标签

| 标签 | 含义 |
|------|------|
| `CBN_UI_SDK` | 国网 UI SDK |
| `CBN-sdk` | 国网 SDK 核心 |
| `GwSDK` | 网关 SDK |

### 错误模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `loginParams.*$(func://` | Warning | 登录参数未解析 |
| `onGetTabCardsError` | Error | 首页数据获取失败 |
| `HomeDataManager.*不存在` | Warning | 首页数据不存在 |

### 成功模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `CBNSdk.init onLoginSuccess` | Info | 国网 SDK 登录成功 |
| `onGetTabCards list.size:\d+` | Info | TabCards 数据获取成功 |

### 诊断命令

```bash
# 1. 登录状态检查 (核心)
grep -E "onLoginSuccess|onLoginError" <logfile>

# 2. 登录参数
grep "loginParams" <logfile>

# 3. 数据初始化
grep -E "onGetTabCardsError|HomeDataManager.*失败" <logfile>
```

---

## USB Dongle (独立模块)

> **注意**: Dongle 检查与 CBN 登录成功/失败无直接关联。不接 Dongle 也可以成功登录 CBN。

### 关键日志标签

| 标签 | 含义 |
|------|------|
| `DongleManager` | USB 加密狗管理 |
| `DongleProtocol` | 加密狗协议 |

### 错误模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `DongleManager.*openUsbDevice ret = -1` | Error | USB 加密狗打开失败 |
| `DongleManager.*can not find device` | Error | USB 设备未找到 |
| `oid=null.*caid=null` | Error | CA 卡信息为空 |

### 成功模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `deviceAuth true` | Info | 设备认证通过 |

### 诊断命令

```bash
# 1. USB Dongle 状态
grep -E "DongleManager.*openUsbDevice|DongleManager.*can not find" <logfile>

# 2. CA 卡信息
grep -E "oid=|caid=" <logfile>

# 3. 设备认证
grep "deviceAuth" <logfile>
```

---

## HDMI

### 关键日志标签

| 标签 | 含义 |
|------|------|
| `aml_hal_core_detect` | HDMI 检测 |
| `tvhalServer` | TV HAL 服务 |
| `tvhal_client` | TV HAL 客户端 |

### 状态模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `HDMI.*plug in` | Info | HDMI 设备连接 |
| `HDMI.*plug out` | Info | HDMI 设备断开 |

### 诊断命令

```bash
grep -E "HDMI.*plug|getSourceConnectStatus|aml_hal_core_detect.*HDMI" <logfile>
```

---

## Audio / 音频

### 关键日志标签

| 标签 | 含义 |
|------|------|
| `audio_hw_primary` | 音频 HAL |
| `AudioTrack` | 音频轨道 |
| `AudioFlinger` | 音频混合器 |

### 错误模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `audio.*underrun` | Warning | 音频缓冲区欠载 |
| `audio.*(fail|error)` | Error | 音频失败 |

### 诊断命令

```bash
grep -E "audio.*underrun|audio.*fail|AudioTrack|AudioFlinger" <logfile>
```

---

## Network / 网络

### 关键日志标签

| 标签 | 含义 |
|------|------|
| `NET_SDK` | 网络 SDK |
| `NetworkSpeedMonitor` | 速度监控 |

### 错误模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `timeout.*(connect|connection)` | Warning | 连接超时 |
| `disconnect|disconnected` | Warning | 网络断开 |

### 诊断命令

```bash
grep -E "timeout.*connect|disconnect|NetworkSpeedMonitor|NET_SDK" <logfile>
```

---

## Crash / 崩溃

### 错误模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `***.*Build fingerprint` | Critical | Native 崩溃 |
| `ANR in\s+(\S+)` | Critical | 应用无响应 |
| `(Exception|Error):` | Error | Java 异常 |

### 诊断命令

```bash
grep -E "\*\*\*.*Build fingerprint|ANR in|Exception:|Error:" <logfile>
```

---

## Performance / 性能

### 模式

| 模式 | 级别 | 含义 |
|------|------|------|
| `CPU temperatures:\s*\[([\d.]+)\]` | Info | CPU 温度 |
| `skipped\s+(\d+)\s+frames` | Warning | 掉帧 |
| `thermal.*(high|warning|throttle)` | Warning | 过热降频 |

### 诊断命令

```bash
grep -E "Load:|CPU temperatures|skipped.*frames|throttle" <logfile>
```

---

## 案例关键词索引

| 案例 | 名称 | 关键词 | 说明 |
|------|------|--------|------|
| case_001 | CBN 登录失败 | `onGetTabCardsError`, `loginParams`, `oid=null` | 本案例中 Dongle 问题与登录失败同时发生，但非必然因果 |
| case_002 | CBN 登录成功 (有 Dongle) | `onLoginSuccess`, `onGetTabCards`, `loginParams` | 接有 USB Dongle 设备 |
| case_002b | CBN 登录成功 (无 Dongle) | `onLoginSuccess`, `deviceAuthByLocalDevice`, `onGetTabCards` | 使用本地设备 ID 认证 |

---

## 使用建议

1. **从错误级别入手** - 先搜 `E/` 和 `F/` 级别日志
2. **按模块过滤** - 根据问题类型选择对应关键词
3. **关联 PID** - 同一 PID 的日志往往相关
4. **时间窗口** - 问题发生前后 5-10 秒的日志重点分析