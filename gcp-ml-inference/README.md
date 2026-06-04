# EcoLens ML Inference Service

GCP serverless service responsible for wildlife inference, Firestore persistence, tag management, file deletion, and SNS notification triggering.

## Architecture

```text
AWS Lambda
  -> POST processed S3 file information
  -> GCP Cloud Function
  -> Download AI-ready images from S3
  -> Load MegaDetector and species classifier from GCS
  -> Detect and classify wildlife
  -> Write results to Firestore
  -> Publish AWS SNS notification
```

## Technology

- Google Cloud Functions Gen 2
- Google Cloud Storage
- Google Firestore REST API
- AWS S3
- AWS SNS
- MegaDetector `mdv5a.pt`
- Species classifier `model.pt`
- Python 3.11

## Project Files

```text
.
├── main.py
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore
```

Model files are stored in GCS and must not be committed:

```text
gs://<MODEL_BUCKET>/mdv5a.pt
gs://<MODEL_BUCKET>/model.pt
gs://<MODEL_BUCKET>/labels.txt
```

## API Endpoint

Base URL:

```text
https://australia-southeast1-fit5225-a2-aussie-ecolens.cloudfunctions.net/process-file
```

All requests require:

```http
Content-Type: application/json
X-Shared-Secret: <SHARED_SECRET>
```

## Inference API

```http
POST /inference
```

Request from AWS Lambda:

```json
{
  "fileKey": "raw/example.jpg",
  "ai_ready_uris": [
    "s3://bucket/ai-ready/example.jpg"
  ],
  "thumbnail_uri": "s3://bucket/thumb/example.jpg",
  "sha256": "file-checksum",
  "user_id": "user@example.com"
}
```

Response:

```json
{
  "file_id": "generated-file-id",
  "file_key": "raw/example.jpg",
  "status": "processed",
  "tags": {
    "dingo": 1
  },
  "firestore_collection": "media",
  "firestore_doc_id": "generated-file-id"
}
```

## Modify Tags API

```http
POST /tags/modify
```

```json
{
  "urls": ["s3://bucket/raw/example.jpg"],
  "tags": ["kangaroo"],
  "operation": 1
}
```

Operations:

- `1`: add tags
- `0`: remove tags

## Delete Files API

```http
POST /files/delete
```

```json
{
  "urls": ["s3://bucket/raw/example.jpg"]
}
```

Deletes matching Firestore records and associated S3 objects when accessible.

## Subscribe API

```http
POST /subscribe
```

```json
{
  "user_id": "user@example.com",
  "email": "user@example.com",
  "tags": ["dingo", "kangaroo"]
}
```

Stores notification preferences in Firestore.

## Firestore Schema

### `media/{file_id}`

```json
{
  "file_id": "string",
  "file_key": "string | null",
  "user_id": "string | null",
  "file_type": "image | video",
  "file_url": "string",
  "thumbnail_url": "string | null",
  "checksum": "string | null",
  "ai_ready_uris": ["s3://..."],
  "tags": {
    "species": 1
  },
  "auto_tags": ["species"],
  "manual_tags": [],
  "all_tags": ["species"],
  "detections": [
    {
      "species": "dingo",
      "scientific_name": "canis_dingo",
      "classification_confidence": 0.91,
      "detection_confidence": 0.82,
      "bbox": [0.1, 0.2, 0.3, 0.4],
      "source_uri": "s3://..."
    }
  ],
  "status": "processed | failed",
  "error": "present only when failed",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### `subscriptions/{user_id}`

```json
{
  "user_id": "user@example.com",
  "email": "user@example.com",
  "tags": ["dingo", "kangaroo"],
  "status": "active",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

## Environment Variables

See `.env.example`.

Never commit real credentials or secrets.

## Deployment

```bash
gcloud functions deploy process-file \
  --gen2 \
  --runtime=python311 \
  --trigger-http \
  --allow-unauthenticated \
  --region=australia-southeast1 \
  --source=. \
  --entry-point=process_file \
  --memory=2048MB \
  --cpu=1 \
  --timeout=540s \
  --max-instances=2 \
  --set-env-vars=PROJECT_ID=<PROJECT_ID>,AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID>,AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY>,AWS_REGION=ap-southeast-2,SHARED_SECRET=<SHARED_SECRET>,SNS_TOPIC_ARN=<SNS_TOPIC_ARN>,MODEL_BUCKET=<MODEL_BUCKET>,MD_MODEL_KEY=mdv5a.pt,CLASSIFIER_MODEL_KEY=model.pt,LABELS_KEY=labels.txt
```

For production, credentials and secrets should be stored using Secret Manager rather than plain environment variables.
