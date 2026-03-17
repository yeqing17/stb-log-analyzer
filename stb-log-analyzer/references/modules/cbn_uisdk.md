# CBN/UISDK Module (国网 SDK)

国网统一界面 SDK (China Broadcasting Network UI SDK) 模块知识。

## 重要说明

> **USB Dongle 与 CBN 登录是独立的两个模块**
> - Dongle 检查失败 ≠ CBN 登录失败
> - 不接 Dongle 也可以成功登录 CBN
> - 登录成功/失败的判断依据是 `onLoginSuccess` / `onLoginError`

## 登录流程架构

Launcher APK 启动后的登录分为两个层级：

```
┌─────────────────────────────────────────────────────────┐
│  1. Homed 平台登录 (前置条件)                             │
│     └─ access.tsyrmt.cn/account/user/get_list           │
│        └─ ret=0 表示成功                                 │
│           └─ 获取 home_id, user_id, accesstoken 等       │
└─────────────────────────────────────────────────────────┘
                          ↓ 前置成功后
┌─────────────────────────────────────────────────────────┐
│  2. CBN 国网登录 (核心业务)                               │
│     └─ GwSDK.initSDK → GwSDK.login                      │
│        └─ onLoginSuccess / onLoginError                 │
│           └─ 获取 TabCards 首页数据                      │
└─────────────────────────────────────────────────────────┘
```

## Log Tags

- `CBN_UI_SDK` - 国网 UI SDK 主标签
- `CBN-sdk` - 国网 SDK 核心
- `GwSDK` - 网关 SDK
- `ServiceHelper` - Homed 平台 API 请求
- `DongleManager` - USB 加密狗管理 (独立模块)
- `DongleProtocol` - 加密狗协议 (独立模块)

## Homed 平台登录

### 登录接口

| 接口 | 用途 |
|------|------|
| `access.tsyrmt.cn/account/login` | **登录认证** (核心) |
| `access.tsyrmt.cn/account/user/get_list` | 获取用户列表 |

### 成功标志

```
# 登录接口
ServiceHelper: 316ms response for http://access.tsyrmt.cn/account/login
StbApp: monitorAPIResponse onResponse success=true;obj=RespLogin;status=200

# 用户列表接口
ServiceHelper: 35ms response for http://access.tsyrmt.cn/account/user/get_list
StbApp: monitorAPIResponse onResponse success=true;obj=Home;status=200
```

响应体关键字段:
- `ret=0` - 成功
- `home_id` - 家庭 ID
- `user_id` - 用户 ID
- `accesstoken` - 访问令牌

### 失败标志

```
HomedDataSourceManager: getAllChannels not login, skp
ServiceHelper: request failed
```

## CBN 国网登录

### 正常流程

1. **Homed 本地登录** → 获取基础 token
2. **GwSDK.initSDK** → 初始化国网 SDK
3. **GwSDK.login** → 国网认证登录
4. **获取首页数据** → TabCards/pages

### 关键参数

| 参数 | 来源 | 说明 |
|------|------|------|
| `oid` | `ipanel.auth.oid` | 设备组织 ID |
| `caid` | `ipanel.auth.caid` | CA 卡 ID |
| `sn` | `sys.devices.sn` | 设备序列号 |
| `mac` | 设备 MAC | 网络地址 |
| `openId` | CA 卡信息 | 用户身份标识 |

## 常见问题

### 1. USB Dongle 未识别

**Pattern:**
```
DongleManager.*can not find device
DongleManager.*openUsbDevice ret = -1
```

**影响:**
- `oid=null, caid=null`
- 无法完成国网认证
- 后续数据获取失败

**检查项:**
1. USB 加密狗是否插入
2. USB 接口是否正常
3. 加密狗驱动/权限

---

### 2. 登录参数未解析

**Pattern:**
```
loginParams.*\$(func://
```

**正常:**
```
openId=实际的CA卡ID值
```

**异常:**
```
openId=$(func://Object.getAppProp?s_0=ipanel.auth.caid)
```

**原因:**
- CA 卡未识别，无法获取属性值
- 表达式未被正确解析

---

### 3. 数据初始化失败

**Pattern:**
```
onGetTabCardsError
HomeDataManager.*不存在
HomeDataManager.*读取缓存.*失败
```

**Context:**
```
HomeDataManager home不存在
HomeDataManager 读取缓存的页面失败
checkAllNetStatus.*net status : false
onGetTabCardsError 数据初始化失败
```

**可能原因:**
1. 登录未完成/失败
2. 网络不可达
3. 服务器返回错误
4. 本地缓存损坏/不存在

---

### 4. 登录信息有效期

**Pattern:**
```
main--登录信息在有效期
```

**说明:** SDK 认为已登录，跳过重新登录

**注意:**
- 可能掩盖实际的登录问题
- 如需重新登录，需清除缓存

## 诊断步骤

### Step 1: 检查 Dongle 状态

```bash
grep -E "DongleManager.*openUsbDevice|DongleManager.*can not find" <logfile>
```

正常应看到 `ret = 0`，异常则是 `ret = -1`

### Step 2: 检查 CA 卡信息

```bash
grep -E "oid=|caid=|ipanel\.auth" <logfile>
```

确认 `oid` 和 `caid` 是否为有效值（非 null）

### Step 3: 检查登录参数

```bash
grep "loginParams" <logfile>
```

确认参数是否已解析（无 `$(func://` 前缀）

### Step 4: 检查数据获取

```bash
grep -E "onGetTabCards|HomeDataManager|pages.*data" <logfile>
```

## 相关配置

### 缓存路径

```
/storage/emulated/0/Android/data/com.ipanel.join.homed.stb/cache/Standard_home/pages/
```

### 清除缓存重新登录

如有必要，可尝试：
1. 清除应用数据
2. 重新插拔 USB Dongle
3. 重启设备

## Related References

- `modules/network.md` - 网络连接问题
- `cases/case_001_cbn_login_fail.md` - 登录失败案例
- `cases/case_002_cbn_login_success.md` - 登录成功案例（参考）