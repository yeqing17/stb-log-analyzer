# Case 002b: 国网 CBN SDK 登录成功 (无 Dongle)

**Date:** 2026-03-17
**Device:** YQ1600 CBN
**Severity:** Reference (正常流程参考)

## Summary

本文档证明：**不接 USB Dongle 也可以成功登录国网 SDK**。Dongle 检查与 CBN 登录是独立的两个模块。

## 登录流程架构

```
1. Homed 平台登录 (前置条件)
   ├─ access.tsyrmt.cn/account/login (登录认证)
   └─ access.tsyrmt.cn/account/user/get_list (获取用户信息)
      └─ ret=0 表示成功
              ↓
2. CBN 国网登录 (核心业务)
   └─ GwSDK.initSDK → onLoginSuccess
```

## Log Pattern - 完整登录流程

### 0. Homed 平台登录 (前置条件)

```
03-17 16:47:11.575 D ServiceHelper: 35ms response for http://access.tsyrmt.cn/account/user/get_list
03-17 16:47:11.668 D StbApp: monitorAPIResponse onResponse success=true;obj=Home;status=200

03-17 16:47:12.015 D ServiceHelper: 316ms response for http://access.tsyrmt.cn/account/login
03-17 16:47:12.021 D StbApp: monitorAPIResponse onResponse success=true;obj=RespLogin;status=200
```

**关键点:**
- `account/login` - 登录认证接口 (使用本地设备 ID `a0004cda5318`)
- Homed 登录成功后才会进行 CBN 登录

---

## 关键证据

### 1. USB Dongle 未连接

```
03-17 16:47:10.539 D DongleManager: oid=null, caid=null
03-17 16:47:10.550 I DongleManager: buildSupportedUsbDeviceList usb.idongle.alive = []
```

**特征:**
- `usb.idongle.alive = []` - 没有 Dongle 设备
- `oid=null, caid=null` - 初始为空

### 2. Dongle 持续失败 (不影响 CBN 登录)

```
03-17 16:47:10.857 I DongleManager: openUsbDevice ret = -1
03-17 16:47:10.858 I DongleManager: openUsbDevice ret = -1
...
03-17 16:47:10.943 D DongleManager: MSG_DO_OPEN_USB, retry in 5s, count=1, ret=-1
```

**说明:** Dongle 会持续重试（每 5 秒），但这不影响 CBN 登录流程。

---

### 3. 使用本地设备认证 (替代 Dongle)

```
03-17 16:47:11.537 D DongleManager: maybeRetryDeviceAuth hasDongle = false
03-17 16:47:11.537 D DongleManager: deviceAuthByLocalDevice localAuth = 2, hasDeviceId = true
03-17 16:47:11.537 D DongleManager: deviceAuthByLocalDevice deviceNo = a0004cda5318
03-17 16:47:11.551 D DongleManager: oid=a0004cda5318, caid=a0004cda5318
```

**关键点:**
- `hasDongle = false` - 没有 Dongle
- `localAuth = 2` - 使用本地认证
- `deviceNo = a0004cda5318` - 从本地设备获取 ID
- 最终 `oid` 和 `caid` 使用本地设备 ID

---

### 4. CBN 登录成功

```
03-17 16:47:12.030 D MapSelector: run action func://com.ipanel.join.gw_ui_sdk.GwSDK.initSDK/?s_0=ONLINE&s_1=XJSW&s_2=cdd
03-17 16:47:12.044 D GwSDK   : initSDK env = ONLINE, province = XJSW, product = cdd
03-17 16:47:12.064 D CBN_UI_SDK: loginParams: {openId=a0004cda5318, ...}
03-17 16:47:12.866 D CBN_UI_SDK: CBNSdk.init onLoginSuccess
```

**成功标志:**
- `onLoginSuccess` - 登录成功
- `loginParams` 参数已正确解析（使用本地设备 ID）

---

### 5. 数据获取成功

```
03-17 16:47:21.228 D CBN_UI_SDK: onGetTabCards list.size:17
03-17 16:47:27.033 D CBN_UI_SDK: onGetTabCards list.size:16
03-17 16:47:27.425 D CBN_UI_SDK: onGetTabCards list.size:26
```

---

## 对比分析

| 场景 | Dongle 状态 | 认证方式 | CBN 登录 |
|------|-------------|----------|----------|
| case_002 (有 Dongle) | `deviceAuth true` | USB Dongle | 成功 |
| case_002b (无 Dongle) | `openUsbDevice ret = -1` | 本地设备 (`deviceAuthByLocalDevice`) | **成功** |
| case_001 (失败) | `openUsbDevice ret = -1` | 无 (oid=null) | 失败 |

---

## 时序分析

| 时间 | 事件 | 阶段 |
|------|------|------|
| 16:47:10.539 | Dongle 检查开始，无设备 | Dongle |
| 16:47:11.537 | 切换到本地设备认证 | Dongle |
| 16:47:11.575 | Homed user/get_list 响应成功 | **Homed 登录** |
| 16:47:12.015 | Homed account/login 响应成功 | **Homed 登录** |
| 16:47:12.021 | Homed API 确认 RespLogin 成功 | **Homed 登录** |
| 16:47:12.030 | GwSDK.initSDK 调用 | CBN 登录 |
| 16:47:12.044 | GwSDK.initSDK 完成 | CBN 登录 |
| 16:47:12.064 | loginParams 解析完成 | CBN 登录 |
| 16:47:12.866 | **onLoginSuccess** | **CBN 登录成功** |
| 16:47:21.228 | onGetTabCards 成功 | 数据加载 |

**关键时序:**
- Dongle 失败 → 切换本地设备认证 → Homed 登录成功 → CBN 登录成功
- Homed 登录完成后约 9ms 开始 CBN 登录 (12.021 → 12.030)
- CBN 登录耗时约 0.8 秒 (initSDK → onLoginSuccess)

---

## 结论

1. **Dongle 检查与 CBN 登录完全独立**
2. 无 Dongle 时，系统会使用本地设备 ID 进行认证
3. 判断 CBN 登录是否成功的唯一标准是 `onLoginSuccess` / `onLoginError`
4. Dongle 失败日志 (`openUsbDevice ret = -1`) 不应作为 CBN 登录失败的判断依据

---

## Related Cases

- `case_002_cbn_login_success.md` - 有 Dongle 登录成功案例
- `case_001_cbn_login_fail.md` - 登录失败案例
- `modules/cbn_uisdk.md` - CBN SDK 模块知识
