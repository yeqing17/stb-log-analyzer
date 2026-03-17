# HDMI Module

HDMI input/output patterns and diagnostics for Android STB.

## Log Tags

- `tvhal_client` - TV HAL client
- `tvhalServer` - TV HAL server
- `aml_hal_core_detect` - Amlogic HAL detection
- `HDMI` - Generic HDMI events

## Common Patterns

### Connection Events

| Pattern | Level | Description |
|---------|-------|-------------|
| `source.*HDMI.*plug in` | D | HDMI source connected |
| `source.*HDMI.*plug out` | D | HDMI source disconnected |
| `getSourceConnectStatus` | D | Status query |

### Status Values

| Status | Meaning |
|--------|---------|
| `plug in` | Device connected to HDMI port |
| `plug out` | Device disconnected from HDMI port |

## HDMI Ports

Common port naming:
- `HDMI1` - Primary HDMI input
- `HDMI2` - Secondary HDMI input
- `HDMI3` - Tertiary HDMI input (if available)

## Diagnostic Steps

1. **No HDMI signal detected**
   - Search: `plug out`, `plug in`
   - Check detection timing
   - Verify physical connection events

2. **Intermittent HDMI connection**
   - Look for rapid `plug in` / `plug out` cycles
   - Check interval between events
   - May indicate loose cable or hardware issue

3. **HDMI-CEC issues**
   - Search: `CEC`, `cec_`
   - Check CEC command responses
   - Look for CEC timeout messages

## Example Analysis

```
03-09 16:00:46.289 D/aml_hal_core_detect(  395): GetSourceConnectStatus source :HDMI2, status:plug out
```

Interpretation:
- Time: 16:00:46
- Source: HDMI2
- Event: Device disconnected
- PID: 395 (tvhalServer)

## Related References

- `modules/audio.md` - For HDMI audio extraction
- `cases/case_001_hdmi_disconnect.md` - Example HDMI issue