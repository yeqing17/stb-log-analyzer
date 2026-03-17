# 日志分析报告

**文件:** [filename.log]
**设备:** [从日志提取: model/manufacture]
**分析时间:** YYYY-MM-DD HH:MM

---

## 摘要

[一句话描述主要问题或结论]

---

## 登录流程检查 (核心)

> 登录流程: Homed 平台 → CBN 国网 → 首页数据

| 阶段 | 状态 | 关键日志 | 详情 |
|------|------|----------|------|
| Homed 登录 | ✅/❌ | `account/login` 响应 | `ret=0` 表示成功 |
| Homed 用户列表 | ✅/❌ | `user/get_list` 响应 | 获取 home_id, user_id |
| CBN 初始化 | ✅/❌ | `GwSDK.initSDK` | env/province/product |
| CBN 登录 | ✅/❌ | `onLoginSuccess` / `onLoginError` | 核心判断标准 |
| 首页数据 | ✅/❌ | `onGetTabCards` | list.size > 0 表示成功 |

### Dongle 状态 (独立模块)

> 注意: Dongle 与 CBN 登录无直接关联

| 检查项 | 状态 | 详情 |
|--------|------|------|
| USB Dongle | 有/无 | `usb.idongle.alive` |
| 认证方式 | Dongle/本地 | `deviceAuth true` / `deviceAuthByLocalDevice` |
| oid/caid | 有效/null | 有值表示正常 |

---

## 发现的问题

### 1. [问题名称] (Critical/Error/Warning)

**日志位置:** L[行号]
**模式匹配:** `[pattern_name]`
**模块:** [homed/cbn/dongle/audio/network/hdmi/crash]

**日志片段:**
```
[相关日志，包含时间戳]
```

**分析:**
[问题原因分析，引用相关参考文档]

**建议:**
[修复建议，可引用相关案例]

---

## 统计

| 级别 | 数量 | 说明 |
|------|------|------|
| Critical | X | 崩溃/ANR |
| Error | X | 需要关注 |
| Warning | X | 选择性关注 |
| Info | X | 参考信息 |

**模式匹配:** X 个 (来自 keywords.yaml)

---

## 时序分析

[如果涉及登录问题，列出关键时间点]

| 时间 | 事件 | PID | 阶段 |
|------|------|-----|------|
| HH:MM:SS.mmm | 事件描述 | 1234 | Homed/CBN/... |

---

## 相关案例

- [ ] `case_001_cbn_login_fail.md` - CBN 登录失败 (Dongle 问题)
- [ ] `case_002_cbn_login_success.md` - CBN 登录成功 (有 Dongle)
- [ ] `case_002b_cbn_login_success_no_dongle.md` - CBN 登录成功 (无 Dongle)

---

## 使用的诊断命令

```bash
# 模式匹配
python stb-log-analyzer/scripts/pattern_matcher.py [logfile] --module [cbn/homed/dongle]

# 手动搜索
grep -E "onLoginSuccess|onLoginError" [logfile]
grep -E "account/login|user/get_list" [logfile]
```

---

## 附录

### 参考资料

- `references/modules/cbn_uisdk.md` - CBN SDK 模块知识
- `references/keywords.md` - 搜索关键词参考
- `scripts/config/keywords.yaml` - 模式配置
