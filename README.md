# baby-motion

iPhone app for recording and visualizing a baby's motor development using image and video analysis.

## Concept

`baby-motion` turns everyday baby videos into structured growth records.

The app is planned to support:

- Photo and video recording from iPhone
- Pose estimation and motion tracking
- Movement visualization and time-series graphs
- Comparison with previous recordings
- AI-generated observational comments
- Growth timeline by age and milestone

## Initial scope

The first technical milestone is to validate whether pose estimation works reliably enough on baby movement videos, especially rolling over.

### PoC flow

```text
Baby video
   ↓
Frame extraction
   ↓
Pose estimation
   ↓
Keypoint tracking
   ↓
Movement features
   ↓
Visualization / analysis
```

## Planned architecture

- iOS: Swift / SwiftUI
- Backend: Python / FastAPI
- Video analysis: TBD (MediaPipe, MoveNet, Apple Vision, etc.)
- Storage / Cloud: TBD
- AI comments: LLM-based generation from structured movement analysis

## Development phases

1. Pose estimation PoC
2. Motion analysis
3. Backend API
4. iPhone MVP
5. AI-generated comments
6. Growth visualization
7. Timeline and historical comparison

## Privacy

This repository must not contain real baby photos, videos, personal information, credentials, or production data.

Use synthetic or explicitly non-sensitive sample data for development and testing.

## Status

Early prototype / technical validation.
