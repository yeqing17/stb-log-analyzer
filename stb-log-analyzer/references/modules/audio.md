# Audio Module

Audio subsystem patterns and diagnostics for Android STB.

## Log Tags

- `audio_hw_primary` - Primary audio HAL
- `AudioTrack` - Audio track playback
- `AudioFlinger` - Audio mixer
- `AudioPolicy` - Audio routing policy

## Common Patterns

### Normal Operations

| Pattern | Level | Description |
|---------|-------|-------------|
| `in_get_format.*hal_format=1` | V | Format query (verbose, high frequency) |
| `in_read.*bytes 8192` | V | Audio data read |
| `audio_stream_in_frame_size` | V | Frame size calculation |

### Warnings

| Pattern | Description | Action |
|---------|-------------|--------|
| `audio.*underrun` | Buffer underrun | Check CPU load, buffer size |
| `AudioTrack.*disable` | Track disabled | Check audio focus |

### Errors

| Pattern | Description | Action |
|---------|-------------|--------|
| `audio.*fail` | General failure | Check audio HAL status |
| `cannot open audio device` | Device unavailable | Check permissions, HAL |
| `audio.*timeout` | Operation timeout | Check for deadlock |

## Diagnostic Steps

1. **Audio dropouts**
   - Search: `audio.*underrun`
   - Check surrounding context for CPU spikes
   - Look for competing processes

2. **No audio output**
   - Search: `AudioPolicy`, `AudioTrack`
   - Check routing decisions
   - Verify stream type and device selection

3. **Audio delay**
   - Search for buffer-related messages
   - Check `AudioFlinger` for mixer delays
   - Look for `in_read` timing gaps

## Related References

- `errors/performance.md` - For underrun analysis
- `cases/` - Historical audio issue cases