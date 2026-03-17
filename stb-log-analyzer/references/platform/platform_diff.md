# 平台差异对比

Android TV、Android STB ROM 与 Linux 机顶盒日志分析的关键差异。

## 平台类型总览

| 平台类型 | 说明 | 日志来源 |
|----------|------|----------|
| **Android TV** | Android TV + homed APK | logcat 标准格式 |
| **Android STB ROM** | Android 机顶盒 ROM + homed APK | logcat 带 TID 格式 |
| **Linux STB** | Linux 机顶盒 + iPanel中间件 | 自定义格式 |

## 日志格式对比

| 特性 | Android TV (logcat) | Android STB ROM (logcat) | Linux STB (自定义) |
|------|---------------------|--------------------------|-------------------|
| 时间戳 | `MM-DD HH:MM:SS.mmm` | `MM-DD HH:MM:SS.mmm` | `[tm:XXX]` 毫秒 |
| 进程标识 | `Tag(PID)` | `PID TID` | `[tid:XXX]` hex |
| 线程标识 | 无 | `TID` 独立字段 | 在tid字段中 |
| 级别标记 | `Level/` 前缀 | `Level` 空格分隔 | `[Level]` 方括号 |
| 来源标识 | Tag 标签 | Tag 标签 | 源码路径 |

## Android logcat 格式详解

### 1. Android TV 标准格式

```
MM-DD HH:MM:SS.mmm Level/Tag(PID): Message
```

**示例:**
```
03-09 16:00:46.289 D/aml_hal_core_detect( 395): GetSourceConnectStatus...
```

**字段说明:**

| 字段 | 示例 | 说明 |
|------|------|------|
| 时间戳 | `03-09 16:00:46.289` | 月-日 时:分:秒.毫秒 |
| 级别 | `D` | V=Verbose, D=Debug, I=Info, W=Warn, E=Error, F=Fatal |
| 标签 | `aml_hal_core_detect` | 日志来源组件 |
| PID | `395` | 进程 ID |
| 消息 | `GetSourceConnectStatus...` | 具体内容 |

### 2. Android STB ROM 格式 (带TID)

```
MM-DD HH:MM:SS.mmm PID TID Level Tag: Message
```

**示例:**
```
01-01 08:00:00.312  2069  2069 W auditd  : type=2000 audit(0.0:1): initialized
01-01 08:00:03.294  1950  2060 I hwc     : get valid power Mode =2
01-01 08:00:03.294  1950  2060 E hwc     : change composition type layer is empty
```

**字段说明:**

| 字段 | 示例 | 说明 |
|------|------|------|
| 时间戳 | `01-01 08:00:00.312` | 月-日 时:分:秒.毫秒 |
| PID | `2069` | 进程 ID |
| TID | `2069` | 线程 ID (可能与PID相同) |
| 级别 | `W` | V/D/I/W/E/F |
| 标签 | `auditd` | 日志来源组件 |
| 消息 | `type=2000 audit...` | 具体内容 |

**与 Android TV 的主要差异:**

1. **包含 TID (线程ID)** - 可以追踪多线程问题
2. **格式更紧凑** - PID/TID 在级别之前
3. **SELinux审计日志更多** - 常见 `auditd`, `SELinux` 标签

### 常见标签

| 标签 | 含义 |
|------|------|
| `ActivityManager` | 应用管理器 |
| `AudioFlinger` | 音频混合 |
| `SurfaceFlinger` | 图形合成 |
| `AudioTrack` | 音频播放轨道 |
| `PackageManager` | 包管理 |
| `dalvikvm/art` | 虚拟机 |
| `auditd` | SELinux 审计 |
| `SELinux` | SELinux 策略 |
| `hwc` | Hardware Composer |
| `cec_hal` | HDMI CEC 控制 |

### 特有事件

- **ANR**: `ANR in <package>` - 应用无响应
- **Native Crash**: `*** Build fingerprint` - 本地崩溃
- **GC**: `GC_FOR_ALLOC`, `GC_CONCURRENT` - 垃圾回收
- **SELinux Denial**: `avc: denied` - SELinux 拒绝访问

## Linux STB 自定义格式详解

### iPanel 中间件格式

```
[Level][tm:XXX][tid:XXXXXXXX] Message
```

**示例:**
```
[I][93][porting_display_init:78](in)
[W][206][porting_stbinfo_init:470]sn:08A9102010020030002038FACA19BDF3
[tm=52][tid:40bdf2b0] config.ini item: homed-use-icc-livetv = 1
```

### 字段说明

| 字段 | 示例 | 说明 |
|------|------|------|
| 级别 | `[I]`, `[W]` | I=Info, W=Warn, E=Error |
| 时间戳 | `tm:93`, `tm=52` | 启动后的毫秒数 |
| 线程ID | `tid:40bdf2b0` | 十六进制线程ID |
| 消息 | `porting_display_init:78](in)` | 包含源码位置 |

### 常见消息模式

```bash
# 初始化消息
[I][93][porting_display_init:78](in)

# 配置项
[tm=52][tid:40bdf2b0] config.ini item: homed-use-icc-livetv = 1

# 错误消息
<ERROR>mount /dev/sda1 on /mnt type vfat failed!

# HDMI 事件
--- Get HDMI event: HOTPLUG. ---
[HDMI Plug  g_DispHdmiHotPlugflag :1]

# 音频错误
[7479 ERROR-ao]:HI_UNF_SND_GetSampleRate[638]:Get AO Attr failed, ERR:0x80130041
```

## 分析策略差异

### Android TV 分析重点

1. **应用层问题**
   - ANR 分析：检查主线程阻塞
   - Java 异常：获取完整堆栈
   - 生命周期问题

2. **系统服务**
   - ActivityManager 事件
   - PackageManager 问题
   - SurfaceFlinger 渲染问题

3. **性能指标**
   - GC 频率和耗时
   - 掉帧 (skipped frames)
   - 内存压力

### Android STB ROM 分析重点

1. **SELinux 审计**
   - `avc: denied` 权限拒绝
   - 策略配置问题
   - permissive 模式警告

2. **HAL 层问题**
   - Hardware Composer 错误
   - HDMI CEC 通信
   - 音视频硬件接口

3. **多线程问题**
   - 利用 TID 追踪线程
   - 跨进程通信

### Linux STB 分析重点

1. **内核问题**
   - 驱动错误
   - 硬件中断
   - 设备枚举

2. **系统资源**
   - 内存 OOM
   - CPU 调度
   - 存储错误

3. **中间件问题**
   - iPanel 初始化
   - DVB 栈状态
   - 配置加载

## 常见问题对照表

| 问题类型 | Android TV | Android STB ROM | Linux STB |
|----------|------------|-----------------|-----------|
| 崩溃 | `*** Build fingerprint` | `*** Build fingerprint` | `segfault`, `Oops` |
| 无响应 | `ANR in` | `ANR in` | `blocked for more than` |
| 内存不足 | `Out of memory`, `LMK` | `Out of memory`, `LMK` | `Out of memory` |
| USB 问题 | `USB`, `usb_device` | `USB`, `usb_device` | `USB disconnect` |
| 网络断开 | `disconnect` | `disconnect` | `link down` |
| 音频问题 | `AudioTrack`, `underrun` | `AudioTrack`, `underrun` | `ERROR-ao`, `alsa` |
| SELinux | 较少 | `avc: denied` | 无 |
| HDMI | `HDMI.*plug` | `cec_hal`, `HDMI` | `HDMI event` |

## 脚本使用

### log_parser.py

自动检测平台类型并解析:

```bash
# 解析日志（自动检测平台）
python log_parser.py logs/android-stb-rom.log
python log_parser.py logs/linux-stb.log

# 输出示例:
# Parsed 36199 entries
# 平台分布:
#   android_stb_rom: 36199 entries
```

### pattern_matcher.py

模式匹配支持所有平台:

```bash
# 匹配错误模式
python pattern_matcher.py logs/android-stb-rom.log

# 按模块过滤
python pattern_matcher.py logs/android-stb-rom.log --module cbn
```

## 平台特定关键词

### Android STB ROM 特有

```yaml
# SELinux 相关
- pattern: "avc:\\s*denied"
  description: "SELinux 权限拒绝"

# HAL 层
- pattern: "HwcFbFreshfbHandle is null"
  description: "显示缓冲区为空"

# CEC
- pattern: "cec_hal.*ret"
  description: "HDMI CEC 返回值"
```

### Linux STB 特有

```yaml
# iPanel
- pattern: "\\[ERROR-ao\\]"
  description: "音频输出错误"

- pattern: "mount.*failed"
  description: "挂载失败"
```