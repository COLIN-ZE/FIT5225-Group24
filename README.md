# FIT5225-Group24

AussieEcoLense is a FIT5225 Assignment 2 project for Australian wildlife image/video detection.

## Project Structure

```text
frontend/       Vue 3 + Vite web UI
gcp-query-api/  Member D GCP Cloud Function query API skeleton
test_images/    Sample wildlife images for testing
AussieEcoLense/ Local model package, ignored by Git
```

## Member D Status

The frontend query workflow is implemented with mock data and can be demonstrated before members B/C finish the processing pipeline:

```text
All / Tag / Species / Count / Thumbnail / File query modes
Thumbnail preview
Single-file tag updates
Batch tag updates
Delete flow
Upload / Query navigation
```

The real API integration is prepared in `gcp-query-api/` and `frontend/src/api/query.js`. It is waiting on the Firestore schema and Cloud Function URL from members B/C.
