# ICC 快速切台模块

ICC (Inter-Channel Change) 快速切台问题分析，用于诊断 **ICC流无法切换到UDP组播流** 的问题。

## 背景

### ICC + UDP 快速切台机制

机顶盒快速切台的实现方式：
1. **用户切台** → 先播放 ICC 流（快速响应，低延迟）
2. **后台加载** → 同时获取目标 UDP 组播流
3. **无缝切换** → 当 UDP 流准备好后，从 ICC 流切换到 UDP 组播流

### 问题现象

**ICC 流无法切换到 UDP 流**：
- 一直播放 ICC 流，没有切换到 UDP
- 没有快速切台效果，用户看到的是低画质 ICC 流

## 问题原因：PTS 时间戳异常

### PTS 基础

- **单位**: 90kHz 时钟周期
- **换算**: 1秒 = 90000 单位，1ms ≈ 90 单位
- **正常差值**: UDP流与ICC流的 PTS 差值应在几百毫秒内

### 典型故障

**日志特征**:
```
find a iframe!pts=60323127!!icc_first_pts=89618269,first_get_block_system_time=17095 ms,now:148767 ms
```

**问题分析**:

| 项目 | 值 | 说明 |
|------|-----|------|
| UDP流 PTS | 60,323,127 | 目标切换流 |
| ICC流 PTS | 89,618,269 | 当前播放流 |
| PTS 差值 | -29,295,142 | UDP < ICC |
| 时间差 | ~325 秒 | **无法同步！** |

**结论**: UDP流的PTS比ICC流PTS小约2900万单位（~325秒），差异过大导致无法完成 ICC→UDP 切换，系统只能持续播放 ICC 流。

### 正常情况对比

```
find a iframe!pts=71820936!!icc_first_pts=71820456,...
```

| 项目 | 值 |
|------|-----|
| UDP流 PTS | 71,820,936 |
| ICC流 PTS | 71,820,456 |
| PTS 差值 | 480 (~5ms) |
| 结果 | **正常切换** |

## 日志来源

- **Tag**: `mplayer-jni`
- **源文件**: `ilocal_icclive_player.c`
- **函数**: `ilocal_icclive_player_proc`

### 关键日志格式

```
find a iframe!pts=<UDP流PTS>!!icc_first_pts=<ICC流PTS>,first_get_block_system_time=<ICC开始时间> ms,now:<当前时间> ms
```

### 字段说明

| 字段 | 含义 | 示例值 |
|------|------|--------|
| `pts` | UDP 组播流的 I 帧 PTS | 60323127 |
| `icc_first_pts` | ICC 流起始 I 帧 PTS | 89618269 |
| `first_get_block_system_time` | ICC 流开始获取的系统时间 | 17095 ms |
| `now` | 当前系统运行时间 | 148767 ms |

## 频道信息

ICC 问题分析时，可结合频道信息定位具体频道：

### 频道信息日志格式

```
getAllChannels chnl_name=<频道名称>, chnl_num=<频道号>serviceId=<服务ID>,channelid:<频道ID>
```

### 示例

```
chnl_name=CCTV-1高清, chnl_num=1serviceId=101,channelid:4200000953
```

### 诊断命令

```bash
# 提取频道列表
grep "getAllChannels" <logfile> | head -20

# 查找问题时间点的播放频道
grep -B 100 "find a iframe.*pts=.*icc_first_pts" <logfile> | grep -E "chnl_name|playChannel"
```

## 诊断方法

### 1. 使用模块分析

```bash
python stb-log-analyzer/scripts/pattern_matcher.py <logfile> --module icc_switch
```

### 2. 手动提取 PTS 数据

```bash
grep "find a iframe.*pts=.*icc_first_pts" <logfile>
```

### 3. 计算 PTS 差值

```bash
# 提取并计算差值
grep "find a iframe.*pts=" <logfile> | \
  awk -F'pts=' '{split($2,a,"!!"); split(a[2],b,"="); print a[1], b[2], a[1]-b[2]}'
```

## 判断标准

| PTS 差值 (UDP - ICC) | 状态 | 说明 |
|---------------------|------|------|
| ±50000 (±500ms) | 正常 | 可以正常切换到 UDP |
| ±50000 ~ ±500000 | 警告 | 切换可能延迟 |
| > ±500000 | **异常** | **无法切换，只播 ICC** |

## 可能原因

1. **流源问题**
   - UDP 组播流 PTS 不连续
   - 编码器 PTS 重置
   - 不同频道 PTS 基准不同

2. **网络问题**
   - UDP 丢包导致 PTS 跳变
   - 组播流延迟过大

3. **系统问题**
   - 解码器缓存未及时清理
   - ICC 流与 UDP 流时钟不同步

## 解决建议

| 原因 | 解决方案 |
|------|----------|
| 流源 PTS 异常 | 检查编码器配置，确保 PTS 连续 |
| 网络丢包 | 检查组播网络质量 |
| 时钟不同步 | 检查系统时钟同步机制 |

## 相关参考

- `network.md` - 网络问题导致流异常
- `audio.md` - 音视频同步问题
