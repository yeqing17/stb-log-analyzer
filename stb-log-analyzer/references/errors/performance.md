# Performance Issues

Patterns for detecting performance degradation in STB logs.

## Key Indicators

### CPU Load

**Pattern:**
```
Load: [\d.]+ / [\d.]+ / [\d.]+
```

**Interpretation:**
- First value: 1-minute average
- Second value: 5-minute average
- Third value: 15-minute average

**Thresholds:**
| Load | Status |
|------|--------|
| < core_count | Normal |
| ~ core_count | Busy |
| > core_count | Overloaded |

---

### Memory Pressure

**Patterns:**
```
Low memory
Out of memory
LMK.*kill
```

**Indicators:**
- Frequent GC messages
- Memory allocation failures
- Process kills by LMKD

---

### Audio Underrun

**Pattern:**
```
audio.*underrun
```

**Causes:**
- High CPU load
- Thread starvation
- Insufficient buffer size

**Action:**
1. Check CPU load at same timestamp
2. Look for competing processes
3. Consider buffer size adjustment

---

### Frame Drops

**Pattern:**
```
(frame|frames).*drop
Choreographer.*skipped
```

**Context:**
```
Choreographer: Skipped 60 frames!  The application may be doing too much work on its main thread.
```

**Severity:** Warning

---

### Network Bandwidth

**From:**
```
NetworkSpeedMonitor
```

**Context:**
```
Download Speed: 2014 bytes/sec
Upload Speed: 7447 bytes/sec
```

**Thresholds for streaming:**
| Speed | Quality |
|-------|---------|
| < 1 Mbps | Low quality / buffering risk |
| 1-5 Mbps | SD quality |
| 5-15 Mbps | HD quality |
| > 15 Mbps | 4K possible |

---

### Thermal Throttling

**Pattern:**
```
thermal.*(high|warning|throttle)
CPU temperatures: [\d.]+
```

**From logs:**
```
03-09 16:00:46.123 I/ThermalService( 1042): CPU temperatures: [30.800001]
```

**Thresholds:**
| Temperature | Status |
|-------------|--------|
| < 45°C | Normal |
| 45-60°C | Warm |
| 60-75°C | Hot, may throttle |
| > 75°C | Critical |

---

## Analysis Workflow

1. **Gather baseline**
   - Normal CPU load range
   - Typical memory usage
   - Expected network speeds

2. **Identify anomalies**
   - Spikes in load
   - Memory growth over time
   - Network degradation

3. **Correlate events**
   - Match performance issues with user actions
   - Check for background processes
   - Look for resource contention

---

## Related References

- `crash_patterns.md` - ANR analysis
- `modules/audio.md` - Audio underrun details
- `modules/network.md` - Network bandwidth issues