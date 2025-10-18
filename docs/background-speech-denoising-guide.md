# Background Speech Denoising Configuration Guide

## Overview

Background speech denoising helps improve call quality by reducing or eliminating unwanted background noise during conversations. This feature is particularly useful for assistants operating in noisy environments like call centers, outdoor settings, or public spaces.

Vapi provides two denoising methods:
1. **Smart Denoising** - AI-powered, automatic, recommended for most use cases
2. **Fourier Denoising** - Advanced frequency-based denoising with fine-grained control

## How It Works

Background speech denoising analyzes the audio stream in real-time and separates speech from background noise. The processed audio preserves voice clarity while reducing unwanted sounds like:
- Traffic noise
- Office chatter
- Music and TV
- Wind and environmental sounds
- Static and electrical interference

**Important Notes:**
- Both denoising methods can be enabled simultaneously
- Smart denoising is recommended for most use cases
- Fourier denoising provides advanced controls for specific scenarios
- Denoising is applied to the customer's audio before transcription

## Configuration Structure

Add `backgroundSpeechDenoisingPlan` to your `assistant.yaml` file:

```yaml
# assistant.yaml

name: "Your Assistant"
voice:
  provider: azure
  voiceId: andrew

model:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.7

# Background speech denoising configuration
backgroundSpeechDenoisingPlan:
  smartDenoisingPlan:
    enabled: true
  fourierDenoisingPlan:
    enabled: false
```

## Configuration Options

### Smart Denoising Plan

AI-powered denoising that intelligently detects and removes background noise while preserving speech quality.

```yaml
backgroundSpeechDenoisingPlan:
  smartDenoisingPlan:
    enabled: true  # Enable smart denoising
```

**When to use:**
- General-purpose noise reduction
- Variable noise environments
- When you want automatic optimization
- Most production use cases

### Fourier Denoising Plan

Advanced frequency-domain denoising with fine-grained controls for specific scenarios.

```yaml
backgroundSpeechDenoisingPlan:
  fourierDenoisingPlan:
    enabled: true
    mediaDetectionEnabled: true      # Detect and preserve media (music, TV)
    staticThreshold: -35             # Noise floor threshold in dB
    baselineOffsetDb: -15            # Offset from baseline noise level in dB
    windowSizeMs: 3000               # Analysis window size in milliseconds
    baselinePercentile: 85           # Percentile for baseline calculation
```

**Parameters:**

- **enabled** (boolean): Enable Fourier denoising
  - Default: `false`

- **mediaDetectionEnabled** (boolean): Automatically detect and preserve media like music or TV
  - Default: `true`
  - Set to `false` if you want aggressive denoising regardless of media

- **staticThreshold** (integer): Noise floor threshold in decibels
  - Default: `-35` dB
  - Lower values (e.g., `-40`) = more aggressive noise removal
  - Higher values (e.g., `-30`) = more conservative, preserves more audio

- **baselineOffsetDb** (integer): Offset from the calculated baseline noise level
  - Default: `-15` dB
  - Adjusts the denoising threshold relative to detected baseline
  - Lower values = more aggressive denoising

- **windowSizeMs** (integer): Analysis window size in milliseconds
  - Default: `3000` ms (3 seconds)
  - Larger windows = more accurate baseline but slower adaptation
  - Smaller windows = faster adaptation to changing noise

- **baselinePercentile** (integer): Percentile for baseline noise calculation
  - Default: `85` (85th percentile)
  - Higher values = more conservative baseline estimation
  - Lower values = more aggressive baseline estimation

**When to use:**
- Specific noise patterns require tuning
- You need media detection control
- Call center environments with predictable noise
- Technical scenarios requiring precise control

## Examples

### Simple Smart Denoising (Recommended)

```yaml
# assistant.yaml

name: "Customer Support Assistant"
voice:
  provider: azure
  voiceId: andrew

model:
  provider: anthropic
  model: claude-3-opus-20240229
  temperature: 0.7

backgroundSpeechDenoisingPlan:
  smartDenoisingPlan:
    enabled: true
```

### Fourier Denoising with Default Settings

```yaml
backgroundSpeechDenoisingPlan:
  fourierDenoisingPlan:
    enabled: true
    mediaDetectionEnabled: true
    staticThreshold: -35
    baselineOffsetDb: -15
    windowSizeMs: 3000
    baselinePercentile: 85
```

### Aggressive Denoising for Noisy Environments

Use lower thresholds for environments with high background noise:

```yaml
backgroundSpeechDenoisingPlan:
  fourierDenoisingPlan:
    enabled: true
    mediaDetectionEnabled: false    # Disable to remove all background sounds
    staticThreshold: -40            # More aggressive threshold
    baselineOffsetDb: -20           # More aggressive offset
    windowSizeMs: 2000              # Faster adaptation
    baselinePercentile: 80          # More aggressive baseline
```

### Conservative Denoising for Clean Environments

Use higher thresholds when you want to preserve more of the original audio:

```yaml
backgroundSpeechDenoisingPlan:
  fourierDenoisingPlan:
    enabled: true
    mediaDetectionEnabled: true
    staticThreshold: -30            # Less aggressive threshold
    baselineOffsetDb: -10           # Less aggressive offset
    windowSizeMs: 4000              # Longer analysis window
    baselinePercentile: 90          # Conservative baseline
```

### Combined Smart and Fourier Denoising

You can enable both methods simultaneously for maximum noise reduction:

```yaml
backgroundSpeechDenoisingPlan:
  smartDenoisingPlan:
    enabled: true
  fourierDenoisingPlan:
    enabled: true
    mediaDetectionEnabled: true
    staticThreshold: -35
    baselineOffsetDb: -15
    windowSizeMs: 3000
    baselinePercentile: 85
```

### Call Center Configuration

Optimized for typical call center environments:

```yaml
backgroundSpeechDenoisingPlan:
  smartDenoisingPlan:
    enabled: true
  fourierDenoisingPlan:
    enabled: true
    mediaDetectionEnabled: false    # Remove office chatter and sounds
    staticThreshold: -38
    baselineOffsetDb: -18
    windowSizeMs: 2500
    baselinePercentile: 82
```

### Outdoor/Mobile Configuration

Optimized for outdoor or mobile environments with wind and traffic:

```yaml
backgroundSpeechDenoisingPlan:
  smartDenoisingPlan:
    enabled: true
  fourierDenoisingPlan:
    enabled: true
    mediaDetectionEnabled: true
    staticThreshold: -40            # Aggressive for outdoor noise
    baselineOffsetDb: -20
    windowSizeMs: 2000              # Fast adaptation for changing conditions
    baselinePercentile: 80
```

## Use Cases by Industry

### Customer Support & Call Centers
```yaml
backgroundSpeechDenoisingPlan:
  smartDenoisingPlan:
    enabled: true
```
Simple smart denoising handles varied customer environments effectively.

### Healthcare & Telehealth
```yaml
backgroundSpeechDenoisingPlan:
  smartDenoisingPlan:
    enabled: true
  fourierDenoisingPlan:
    enabled: false
```
Smart denoising ensures clear communication in clinical settings.

### Field Services & Mobile Workers
```yaml
backgroundSpeechDenoisingPlan:
  smartDenoisingPlan:
    enabled: true
  fourierDenoisingPlan:
    enabled: true
    mediaDetectionEnabled: true
    staticThreshold: -40
    windowSizeMs: 2000
```
Combined denoising with fast adaptation for outdoor environments.

### Restaurant & Hospitality
```yaml
backgroundSpeechDenoisingPlan:
  smartDenoisingPlan:
    enabled: true
  fourierDenoisingPlan:
    enabled: true
    mediaDetectionEnabled: false
    staticThreshold: -38
```
Aggressive denoising to handle background music and crowd noise.

## Best Practices

1. **Start with Smart Denoising**: Enable smart denoising first and test before adding Fourier denoising
2. **Test in Real Conditions**: Verify denoising performance in your actual deployment environment
3. **Monitor Transcription Quality**: Check if aggressive denoising affects transcription accuracy
4. **Adjust Incrementally**: Make small adjustments to Fourier parameters (±5 dB at a time)
5. **Consider Media**: Enable `mediaDetectionEnabled` unless you specifically want to remove all background sounds
6. **Balance Quality vs Noise**: More aggressive denoising may affect voice quality
7. **Use Combined Approach**: For very noisy environments, enable both smart and Fourier denoising

## Deploying

After configuring background speech denoising in your `assistant.yaml`, deploy your assistant:

```bash
# Create new assistant
vapi-manager assistant create your-assistant-name

# Update existing assistant
vapi-manager assistant update your-assistant-name
```

## Testing

Test denoising by:
1. Start a call with your assistant in the target environment
2. Speak with typical background noise present
3. Review call transcripts for accuracy
4. Listen to recordings to verify noise reduction
5. Adjust parameters based on results
6. Test again until satisfied

### Testing Checklist

- [ ] Test in quiet environment (baseline)
- [ ] Test with background music/TV
- [ ] Test with multiple people talking
- [ ] Test with traffic/outdoor noise
- [ ] Test with office equipment noise
- [ ] Verify transcription accuracy
- [ ] Check voice quality preservation

## Troubleshooting

**Voice sounds muffled or distorted:**
- Reduce denoising aggressiveness
- Increase `staticThreshold` (e.g., from -35 to -30)
- Increase `baselineOffsetDb` (e.g., from -15 to -10)
- Disable Fourier denoising if using both methods

**Background noise still present:**
- Enable both smart and Fourier denoising
- Lower `staticThreshold` (e.g., from -35 to -40)
- Lower `baselineOffsetDb` (e.g., from -15 to -20)
- Set `mediaDetectionEnabled` to `false` for aggressive removal

**Media (music/TV) being removed unintentionally:**
- Set `mediaDetectionEnabled` to `true`
- Increase `staticThreshold`
- Use only smart denoising

**Transcription accuracy decreased:**
- Reduce denoising aggressiveness
- Use only smart denoising
- Increase window size for more stable analysis

**Denoising not working:**
- Verify configuration is deployed
- Check that parameters are within valid ranges
- Ensure feature is enabled (`enabled: true`)
- Test with a new call (changes may not affect ongoing calls)

## Parameter Tuning Guide

### Quick Reference

| Environment | staticThreshold | baselineOffsetDb | windowSizeMs | mediaDetectionEnabled |
|-------------|----------------|------------------|--------------|----------------------|
| Quiet       | -30            | -10              | 4000         | true                 |
| Moderate    | -35            | -15              | 3000         | true                 |
| Noisy       | -40            | -20              | 2000         | false                |
| Very Noisy  | -45            | -25              | 1500         | false                |

### Adjustment Guidelines

**To increase noise removal:**
- ✓ Lower `staticThreshold` by 5 dB
- ✓ Lower `baselineOffsetDb` by 5 dB
- ✓ Set `mediaDetectionEnabled: false`
- ✓ Lower `baselinePercentile` by 5

**To improve voice quality:**
- ✓ Raise `staticThreshold` by 5 dB
- ✓ Raise `baselineOffsetDb` by 5 dB
- ✓ Increase `windowSizeMs` by 500-1000ms
- ✓ Raise `baselinePercentile` by 5

**For changing noise conditions:**
- ✓ Reduce `windowSizeMs` to 1500-2000ms
- ✓ Enable smart denoising
- ✓ Use moderate Fourier settings

## Squad Configuration

For squad configurations, add `backgroundSpeechDenoisingPlan` to the members overrides section:

```yaml
# squad.yaml

name: "Customer Support Squad"
members:
  - assistantId: "your-assistant-id"
    assistantOverrides:
      name: "Support Agent"
      backgroundSpeechDenoisingPlan:
        smartDenoisingPlan:
          enabled: true
        fourierDenoisingPlan:
          enabled: false
```

Or in the squad-level `membersOverrides` to apply to all members:

```yaml
# squad.yaml

name: "Customer Support Squad"
membersOverrides:
  backgroundSpeechDenoisingPlan:
    smartDenoisingPlan:
      enabled: true
```

## Related Documentation

- [Vapi Background Speech Denoising Official Docs](https://docs.vapi.ai/documentation/assistants/conversation-behavior/background-speech-denoising)
- [Vapi Assistant API Reference](https://docs.vapi.ai/api-reference/assistants/create)
- [Analysis Configuration Guide](./analysis-configuration-guide.md)
- [Idle Messages Guide](./idle-messages-guide.md)
