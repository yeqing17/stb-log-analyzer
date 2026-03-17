# 平台差异对比

Android 与 Linux 机顶盒日志分析的关键差异。

## 日志格式对比

| 特性 | Android (logcat) | Linux (syslog/dmesg) |
|------|------------------|----------------------|
| 时间戳 | `MM-DD HH:MM:SS.mmm` | `MMM DD HH:MM:SS` |
| 进程标识 | `Tag(PID)` | `process[pid]:` |
| 级别标记 | `V/D/I/W/E/F` | 文字描述或 priority |
| 来源标识 | Tag 标签 | facility (kernel/daemon/user) |

## Android logcat 详解

### 标准格式

```
MM-DD HH:MM:SS.mmm Level/Tag(PID): Message
```

### 字段说明

| 字段 | 示例 | 说明 |
|------|------|------|
| 时间戳 | `03-09 16:00:46.289` | 月-日 时:分:秒.毫秒 |
| 级别 | `D` | V=Verbose, D=Debug, I=Info, W=Warn, E=Error, F=Fatal |
| 标签 | `aml_hal_core_detect` | 日志来源组件 |
| PID | `395` | 进程 ID |
| 消息 | `GetSourceConnectStatus...` | 具体内容 |

### 常见标签

| 标签 | 含义 |
|------|------|
| `ActivityManager` | 应用管理器 |
| `AudioFlinger` | 音频混合 |
| `SurfaceFlinger` | 图形合成 |
| `AudioTrack` | 音频播放轨道 |
| `PackageManager` | 包管理 |
| `dalvikvm/art` | 虚拟机 |

### 特有事件

- **ANR**: `ANR in <package>` - 应用无响应
- **Native Crash**: `*** Build fingerprint` - 本地崩溃
- **GC**: `GC_FOR_ALLOC`, `GC_CONCURRENT` - 垃圾回收

## Linux syslog/dmesg 详解

### syslog 格式

```
MMM DD HH:MM:SS hostname process[pid]: Message
```

示例：
```
Mar  9 16:00:46 stb kernel: [12345.678] usb 1-1: USB disconnect
```

### dmesg 格式

```
[timestamp] Message
```

示例：
```
[12345.678] usb 1-1: USB disconnect, device number 2
```

### 常见来源

| 来源 | 含义 |
|------|------|
| `kernel` | 内核消息 |
| `daemon` | 后台服务 |
| `user` | 用户进程 |
| `local0-7` | 自定义应用 |
| `systemd` | 系统服务管理 |

### 常见消息模式

```bash
# 内核消息
kernel: [xxx] message

# USB 事件
usb 1-1: USB disconnect
usb 1-1: new high-speed USB device

# 网络事件
eth0: link down
eth0: link up, 1000Mbps

# 存储事件
mmcblk0: error -110
sda: write cache enabled

# 内存压力
Out of memory: Kill process
```

## 分析策略差异

### Android 分析重点

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

### Linux 分析重点

1. **内核问题**
   - 驱动错误
   - 硬件中断
   - 设备枚举

2. **系统资源**
   - 内存 OOM
   - CPU 调度
   - 存储错误

3. **网络栈**
   - 网卡状态
   - 协议栈事件
   - socket 错误

## 常见问题对照

| 问题类型 | Android 搜索模式 | Linux 搜索模式 |
|----------|-----------------|----------------|
| 崩溃 | `*** Build fingerprint` | `segfault`, `Oops` |
| 无响应 | `ANR in` | `blocked for more than` |
| 内存不足 | `Out of memory`, `LMK` | `Out of memory`, `Kill process` |
| USB 问题 | `USB`, `usb_device` | `usb`, `USB disconnect` |
| 网络断开 | `disconnect`, `network.*unreachable` | `link down`, `eth0: link` |
| 音频问题 | `audio.*underrun`, `AudioTrack` | `alsa`, `pcm`, `audio` |

## 脚本适配

现有脚本 `log_parser.py` 针对 Android logcat 格式设计。如需分析 Linux 日志，需要：

1. 调整正则表达式匹配 syslog 格式
2. 或使用系统工具：`journalctl`, `dmesg`, `grep`