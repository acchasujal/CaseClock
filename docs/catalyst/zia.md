# Zia

## Capability

Validate Catalyst Zia speech services for:

- English speech to text
- Kannada speech to text
- English text to speech
- Kannada text to speech

This spike validates service suitability only. It must not implement production voice workflows.

## Status

PENDING

No audio samples, transcripts, latency measurements, generated speech files, or Catalyst Zia logs are present in this repository.

## Evidence

### Speech to Text

English test phrase:

```text
Show burglary cases in Bengaluru.
```

Kannada test phrase:

```text
ಬೆಂಗಳೂರಿನ ಕಳ್ಳತನ ಪ್ರಕರಣಗಳನ್ನು ತೋರಿಸಿ.
```

Expected checks:

| Check | English | Kannada | Evidence |
|---|---:|---:|---|
| Recognition succeeds | PENDING | PENDING | Add transcript |
| Meaning preserved | PENDING | PENDING | Add reviewer notes |
| Punctuation acceptable | PENDING | PENDING | Add transcript |
| Latency measured | PENDING | PENDING | Add elapsed time |
| Mixed-language handling acceptable | PENDING | PENDING | Add mixed phrase transcript |

### Text to Speech

English test phrase:

```text
Three burglary cases in Bengaluru are approaching their chargesheet deadline.
```

Kannada test phrase:

```text
ಬೆಂಗಳೂರಿನ ಮೂರು ಕಳ್ಳತನ ಪ್ರಕರಣಗಳು ಆರೋಪಪಟ್ಟಿ ಗಡುವಿನ ಹತ್ತಿರದಲ್ಲಿವೆ.
```

Expected checks:

| Check | English | Kannada | Evidence |
|---|---:|---:|---|
| Audio generation succeeds | PENDING | PENDING | Add generated audio reference |
| Pronunciation acceptable | PENDING | PENDING | Add reviewer notes |
| Clarity acceptable | PENDING | PENDING | Add reviewer notes |
| Speed acceptable | PENDING | PENDING | Add reviewer notes |
| Latency measured | PENDING | PENDING | Add elapsed time |

## Limitations

- Zia usability cannot be decided without recorded audio samples and transcript evidence.
- Kannada STT quality, code-switching, and legal/crime vocabulary recognition are the highest-risk unknowns.
- If Kannada STT is weak, the architecture should keep text input as the reliable fallback instead of modifying frozen API contracts during this spike.

## Decision

PENDING

Record final decisions after validation:

| Service | Decision |
|---|---|
| English STT | PENDING |
| Kannada STT | PENDING |
| English TTS | PENDING |
| Kannada TTS | PENDING |

## Recommendation

Do not rely on Zia voice services for the primary demo path until English and Kannada evidence has been captured and reviewed.
