# Network Module

Network connectivity patterns and diagnostics for Android STB.

## Log Tags

- `NET_SDK` - Network SDK
- `NetworkSpeedMonitor` - Speed monitoring
- `[UDP TUNNEL]` - UDP tunneling
- `[ART-UDPTunnel-L]` - ART UDP tunnel
- `dns_tmr` - DNS timer

## Common Patterns

### Normal Operations

| Pattern | Level | Description |
|---------|-------|-------------|
| `Download Speed: \d+ bytes/sec` | D | Speed monitor report |
| `dns_tmr: dns_check_entries` | D | DNS check timer |
| `vgate.lan nil` | I | Gate resolution |

### Warnings

| Pattern | Description | Action |
|---------|-------------|--------|
| `timeout.*connect` | Connection timeout | Check network, server |
| `socket.*fail` | Socket failure | Check resources, permissions |
| `dns.*fail` | DNS resolution failure | Check DNS config |

### Errors

| Pattern | Description | Action |
|---------|-------------|--------|
| `network.*unreachable` | No route to host | Check connectivity |
| `connection refused` | Server rejected | Check server status |
| `SSL/TLS.*error` | Certificate/protocol error | Check certs, protocol |

## Diagnostic Steps

1. **Slow streaming**
   - Check `NetworkSpeedMonitor` entries
   - Look for `Download Speed` values over time
   - Correlate with playback errors

2. **Connection drops**
   - Search: `disconnect`, `timeout`
   - Trace PID to find affected service
   - Check `UDP TUNNEL` for IPTV issues

3. **DNS issues**
   - Search: `dns`, `resolve`
   - Check `dns_tmr` for periodic failures
   - Look for `vgate.lan` resolution issues

## IPTV Specific

For IPTV streams, monitor:
- `[UDP TUNNEL]` messages
- `onTimerUp` events
- Multicast join/leave messages

## Related References

- `modules/hdmi.md` - For HDMI-CEC network control
- `errors/performance.md` - For bandwidth analysis