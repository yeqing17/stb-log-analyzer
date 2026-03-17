# Case 001: 国网 CBN SDK 登录失败

**Date:** 2024-03-09
**Device:** YQ1600 CBN
**Severity:** High

> **注意**: 本案例中登录失败与 USB Dongle 问题**同时发生**，但这并不代表 Dongle 问题是所有 CBN 登录失败的唯一原因。
> 不接 Dongle 也可以成功登录 CBN（参见 `case_002b`）。Dongle 检查是独立的模块。

## Symptom

用户报告国网首页无法正常加载，提示"数据初始化失败，请稍后重试"。

## Root Cause

本案例中，**USB Dongle（加密狗/CA卡）未正确识别**，导致认证信息无法获取，国网 SDK 登录失败。

## Log Pattern

### 1. USB Dongle 持续失败

```
03-09 16:00:48.557 D/DongleManager( 2964): MSG_DO_OPEN_USB flag = 1
03-09 16:00:48.558 D/DongleManager( 2964): openBindDevice result = -1
03-09 16:00:48.558 D/DongleProtocol( 2964): findUsbDevice type=[vgate-c, vgate-u]
03-09 16:00:48.559 D/DongleProtocol( 2964): can not find device for did=0 vid=9434 pid=34925
03-09 16:00:48.560 I/DongleManager( 2964): openUsbDevice ret = -1
...
03-09 16:00:48.566 D/DongleManager( 2964): MSG_DO_OPEN_USB, retry in 5s, count=13, ret=-1
```

**特征:** 每 5 秒重试一次，持续失败

### 2. CA 卡信息为空

```
03-09 16:01:13.354 D/DongleManager( 9378): oid=null, caid=null
```

### 3. 登录参数未解析

```
03-09 16:01:13.921 D/CBN_UI_SDK( 9378): loginParams: {
  openId=$(func://Object.getAppProp?s_0=ipanel.auth.caid),
  sn=$(func://Object.getAppProp?s_0=ipanel.auth.oid),
  ...
}
```

**问题:** 参数值仍是表达式，未解析为实际值

### 4. 缓存读取失败

```
03-09 16:01:23.291 D/CBN_UI_SDK( 9378): HomeDataManager 读取缓存的pages: /storage/.../page_chunjiexj.data
03-09 16:01:23.292 D/CBN_UI_SDK( 9378): HomeDataManager home不存在
03-09 16:01:23.292 D/CBN_UI_SDK( 9378): HomeDataManager 读取缓存的页面失败
```

### 5. 网络检查失败 + 最终报错

```
03-09 16:01:23.292 I/CBN_UI_SDK( 9378): checkAllNetStatus(), is proxyDevices , net status : false
03-09 16:01:23.292 D/CBN_UI_SDK( 9378): tabid: chunjiexj, hash: 102066417 onGetTabCardsError 数据初始化失败，请稍后重试
```

## Analysis

### 问题链

```
USB Dongle 未识别
       ↓
CA 卡信息获取失败 (oid=null, caid=null)
       ↓
登录参数无法解析 (openId=$(func://...))
       ↓
国网认证失败
       ↓
首页数据获取失败
       ↓
用户看到: "数据初始化失败"
```

### 时序分析

| 时间 | 事件 | PID |
|------|------|-----|
| 16:00:48 | USB Dongle 开始尝试连接 | 2964 |
| 16:00:48~16:01:03 | 持续重试失败 (count=13→15+) | 2964 |
| 16:01:13 | 启动 GwSDK 初始化 | 9378 |
| 16:01:13 | oid/caid 为 null | 9378 |
| 16:01:14 | CBN login 参数未解析 | 9378 |
| 16:01:23 | 首页数据获取失败 | 9378 |

## Recommendation

### 立即检查

1. **物理连接**
   - 确认 USB 加密狗已正确插入
   - 尝试更换 USB 接口
   - 检查加密狗指示灯状态

2. **设备识别**
   ```bash
   adb shell lsusb
   adb shell dmesg | grep -i usb
   ```

3. **权限检查**
   - 确认应用有 USB 设备访问权限

### 如果问题持续

1. 尝试重新插拔加密狗
2. 重启设备
3. 检查加密狗是否损坏（换一台设备测试）
4. 联系硬件供应商确认 Dongle 型号兼容性

## Related Patterns

```bash
# 检查 Dongle 状态
grep -E "DongleManager.*openUsbDevice|DongleManager.*can not find" <logfile>

# 检查 CA 卡信息
grep -E "oid=|caid=" <logfile>

# 检查登录参数
grep "loginParams" <logfile>

# 检查初始化错误
grep -E "onGetTabCardsError|HomeDataManager.*失败" <logfile>
```

## Lessons Learned

1. **USB Dongle 问题是 CBN 登录失败的常见原因**
2. **登录参数中的 `$(func://...)` 表达式表示属性未解析**
3. **"数据初始化失败" 是表象，需要追溯上游登录和认证流程**
4. **不同 PID 的日志需要关联分析** (2964 后台服务 vs 9378 前台应用)

---

# Case Template

**Date:** YYYY-MM-DD
**Device:** [Device Model]
**Severity:** [Low/Medium/High/Critical]

## Symptom

[用户报告的问题现象]

## Root Cause

[根本原因，一句话概括]

## Log Pattern

### [阶段 1 标题]

```
[相关日志]
```

### [阶段 2 标题]

```
[相关日志]
```

## Analysis

### 问题链

```
[上游原因]
    ↓
[下游原因]
    ↓
[最终表现]
```

## Recommendation

1. [建议 1]
2. [建议 2]
3. [建议 3]

## Related Patterns

```bash
# 搜索命令
grep -E "pattern" <logfile>
```

## Lessons Learned

- [经验 1]
- [经验 2]