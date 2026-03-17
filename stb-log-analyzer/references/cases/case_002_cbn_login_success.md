# Case 002: 国网 CBN SDK 登录成功 (有 Dongle)

**Date:** 2026-03-17
**Device:** YQ1600 CBN
**Severity:** Reference (正常流程参考)

## Summary

本文档记录国网 SDK 登录成功的典型日志模式（接有 USB Dongle 设备）。

> **注意**: USB Dongle 与 CBN 登录成功/失败**无直接关联**。不接 Dongle 也可以成功登录 CBN。
> Dongle 检查是独立的流程，参见 `case_002b_cbn_login_success_no_dongle.md`。

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
03-17 16:19:39.603 D ServiceHelper: 34ms response for http://access.tsyrmt.cn/account/user/get_list
03-17 16:19:39.923 D StbApp: monitorAPIResponse onResponse success=true;obj=Home;status=200
```

**关键点:**
- `account/login` - 登录认证接口
- `account/user/get_list` - 获取用户列表
- `ret=0` 表示成功
- 获取 `home_id`, `user_id`, `accesstoken`
- Homed 登录成功后才会进行 CBN 登录

---

### 1. GwSDK 初始化

```
03-17 16:19:40.229 D MapSelector: run action func://com.ipanel.join.gw_ui_sdk.GwSDK.initSDK/?s_0=ONLINE&s_1=XJSW&s_2=cdd
03-17 16:19:40.232 D GwSDK   : initSDK env = ONLINE, province = XJSW, product = cdd
```

**参数说明:**
- `env` = ONLINE (生产环境)
- `province` = XJSW (新疆电网)
- `product` = cdd (产品标识)

---

### 2. 登录参数已正确解析

```
03-17 16:19:40.244 D GwSDK   : login params = {"openId":"9622000003","xinjiangOpenId":"","model":"FamilyMobilePad","sn":"08091B11000010000011221802000003","openIdMode":"SystemProperties,sys.ca.cardid","xinjiangCardType":"","snMode":"SystemProperties,sys.devices.sn","mac":"02:00:00:00:00:00"}
```

**关键点:**
- 参数值均为实际值，无 `$(func://...)` 表达式
- `openId` = `9622000003` (实际值)

---

### 3. 登录成功

```
03-17 16:19:40.341 D UISDK   : main, com.cbn.ibcp.tvlauncheruisdk.UISDK.initSDK(UISDK.kt:496)
03-17 16:19:40.352 D CBN-sdk : main--超过24小时重新登录: 0
03-17 16:19:40.398 D GwSDK   : login end
03-17 16:19:40.399 I GwSDK   : login not proxy net, skip add proxy url
03-17 16:19:40.962 D CBN_UI_SDK: CBNSdk.init onLoginSuccess
03-17 16:19:40.962 D CBN_UI_SDK: 不拦截
```

**成功标志:**
- `CBNSdk.init onLoginSuccess` ← **核心成功标志**
- `login end` 表示登录流程完成

---

### 4. 首页数据获取成功

```
03-17 16:19:57.703 D CBN-sdk : main--登录信息在有效期
03-17 16:19:57.980 D CBN_UI_SDK: onGetTabCards list.size:17
03-17 16:19:57.983 D OkHttp  : --> POST https://launcher-epg.cbntv.net.cn/v1/EPG/WntvUI/GetTabCards
03-17 16:19:58.072 D OkHttp  : <-- 200 OK https://launcher-epg.cbntv.net.cn/v1/EPG/WntvUI/GetTabCards (88ms)
```

**成功标志:**
- `onGetTabCards list.size:17` ← 有数据返回
- `<-- 200 OK` ← HTTP 请求成功
- `登录信息在有效期` ← 后续请求复用登录状态

---

### 5. 页面缓存正常读取

```
03-17 16:20:28.282 D CBN_UI_SDK: HomeDataManager 读取缓存的page chunjiexj 成功
03-17 16:20:29.790 D CBN_UI_SDK: HomeDataManager 保存顶部页面数据 xinjiang_cdd_006 成功
```

---

## USB Dongle 流程 (独立模块)

> 以下为 USB Dongle 相关日志，**与 CBN 登录成功/失败无关**，仅作参考。

### Dongle 识别日志

```
03-17 16:19:38.158 D DongleManager: oid=08091B11000010000011221802000003, caid=9622000003
03-17 16:19:38.182 I DongleManager: deviceAuth true
```

**注意:** 日志中可能有早期的 `openUsbDevice ret = -1` 失败记录，这是初始化过程中的短暂重试，不影响最终结果。

---

## 时序分析

| 时间 | 事件 | 阶段 |
|------|------|------|
| 16:19:39.603 | Homed user/get_list 响应成功 | **Homed 登录** |
| 16:19:39.923 | Homed API 确认 success=true | **Homed 登录** |
| 16:19:40.229 | GwSDK.initSDK 调用 | CBN 登录 |
| 16:19:40.232 | GwSDK.initSDK 完成 | CBN 登录 |
| 16:19:40.244 | login params 解析完成 | CBN 登录 |
| 16:19:40.962 | **onLoginSuccess** | **CBN 登录成功** |
| 16:19:57.980 | onGetTabCards 获取数据 | 数据加载 |
| 16:19:58.072 | GetTabCards HTTP 200 | 数据加载 |

**关键时序:**
- Homed 登录完成后约 300ms 开始 CBN 登录
- CBN 登录耗时约 0.7 秒 (initSDK → onLoginSuccess)

---

## CBN 登录成功判断标准

| 检查项 | 成功标志 |
|--------|----------|
| 登录回调 | `onLoginSuccess` |
| 数据获取 | `onGetTabCards list.size:N` |
| HTTP 状态 | `GetTabCards.*200 OK` |
| 缓存读取 | `读取缓存的page 成功` |

**核心判断:** 看到 `CBNSdk.init onLoginSuccess` 即表示登录成功。

---

## 诊断 Grep 命令

```bash
# 检查登录成功标志 (核心)
grep -E "onLoginSuccess|onLoginError" <logfile>

# 检查登录参数是否解析
grep -E "loginParams|login params" <logfile>

# 检查数据获取
grep -E "onGetTabCards|GetTabCards.*200" <logfile>

# 检查 Dongle 状态 (独立模块，与登录无关)
grep -E "deviceAuth|oid=.*caid=" <logfile>
```

---

## Related Cases

- `case_001_cbn_login_fail.md` - 登录失败案例
- `case_002b_cbn_login_success_no_dongle.md` - 无 Dongle 登录成功案例
- `modules/cbn_uisdk.md` - CBN SDK 模块知识
