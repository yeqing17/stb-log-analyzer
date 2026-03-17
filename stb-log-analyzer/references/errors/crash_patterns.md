# Crash Patterns

Patterns for detecting crashes and serious errors in logcat.

## Crash Types

### Native Crash

**Pattern:**
```
*** Build fingerprint
```

**Context:**
```
*** Build fingerprint: '...'
Revision: '0'
ABI: 'arm64'
```

**Severity:** Critical

**Action:**
1. Locate tombstone file for full stack trace
2. Check signal type (SIGSEGV, SIGABRT, etc.)
3. Identify crashing library

---

### ANR (Application Not Responding)

**Pattern:**
```
ANR in <package_name>
```

**Context:**
```
ANR in com.example.app
Reason: Input dispatching timed out
Load: 5.2 / 4.8 / 3.1
```

**Severity:** Critical

**Common Causes:**
- Main thread blocking
- Deadlock
- Slow I/O on main thread

**Action:**
1. Check CPU load values
2. Look for blocking operations before ANR
3. Review traces.txt for thread states

---

### Java Exception

**Pattern:**
```
(Exception|Error):
```

**Common Types:**

| Exception | Typical Cause |
|-----------|---------------|
| `NullPointerException` | Missing null check |
| `IllegalStateException` | Invalid state transition |
| `SecurityException` | Permission missing |
| `IOException` | File/network failure |
| `RuntimeException` | Programming error |

**Severity:** Error (varies)

**Action:**
1. Get full stack trace
2. Identify throwing class
3. Check recent log entries for root cause

---

## Process Death

**Pattern:**
```
Killing .* (pid=\d+)
```

**Causes:**
- OOM (Out of Memory)
- LMKD (Low Memory Killer)
- Explicit kill

---

## Watchdog Timeout

**Pattern:**
```
Watchdog.*timeout
```

**Severity:** Critical

**Indicates:** System service hung

---

## Detection Script

Use `scripts/pattern_matcher.py` to automatically detect these patterns:

```bash
python pattern_matcher.py <logfile>
```

## Related References

- `performance.md` - For ANR analysis
- `cases/` - Historical crash cases