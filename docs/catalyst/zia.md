# Zia

## Capability

Validate Catalyst Zia speech capabilities for CaseClock.

Expected validation:

- English Speech-to-Text (STT)
- Kannada Speech-to-Text (STT)
- English Text-to-Speech (TTS)
- Kannada Text-to-Speech (TTS)

This spike validates platform availability and suitability only. No production voice workflows were implemented.

---

## Status

⚠️ PARTIALLY COMPLETE

The current Catalyst project does not expose Speech-to-Text or Text-to-Speech services for evaluation.

Available Zia services:

- ✅ Face Analytics
- ✅ OCR
- ✅ Identity Scanner
- ✅ Image Moderation
- ✅ Object Recognition
- ✅ Barcode Scanner
- ✅ AutoML
- ✅ Text Analytics

Unavailable during validation:

- ❌ Speech-to-Text
- ❌ Text-to-Speech

---

## Validation Results

### Speech-to-Text

| Feature | Result | Notes |
|---------|--------|-------|
| English STT | NOT AVAILABLE | Speech service not exposed in current Catalyst project |
| Kannada STT | NOT AVAILABLE | Speech service not exposed in current Catalyst project |

---

### Text-to-Speech

| Feature | Result | Notes |
|---------|--------|-------|
| English TTS | NOT AVAILABLE | Speech service not exposed in current Catalyst project |
| Kannada TTS | NOT AVAILABLE | Speech service not exposed in current Catalyst project |

---

## Observations

The Catalyst project used during technical validation provides several Zia AI capabilities focused on image analysis and text analytics.

However, Speech-to-Text and Text-to-Speech services were not available in the project dashboard and therefore could not be evaluated.

Because these services were unavailable, no conclusions can be drawn regarding:

- English transcription quality
- Kannada transcription quality
- English speech synthesis
- Kannada speech synthesis
- Voice latency
- Pronunciation quality
- Mixed-language support

This is an availability limitation rather than a platform failure.

---

## Limitations

The following capabilities could not be validated because they were unavailable in the current Catalyst project:

- English Speech-to-Text
- Kannada Speech-to-Text
- English Text-to-Speech
- Kannada Text-to-Speech

If future project access enables these services, the following should be evaluated:

- Recognition accuracy
- Kannada language support
- Crime terminology recognition
- Audio quality
- Latency
- Mixed-language support

---

## Decision

| Service | Decision |
|----------|----------|
| English STT | Could not evaluate |
| Kannada STT | Could not evaluate |
| English TTS | Could not evaluate |
| Kannada TTS | Could not evaluate |

---

## Recommendation

Voice functionality should not be considered part of the primary CaseClock demonstration until Speech-to-Text and Text-to-Speech services are available for validation.

The current project can safely proceed using text-based interaction, while voice support remains a future enhancement pending access to the required Zia speech capabilities.

No architecture changes are required based on this validation.