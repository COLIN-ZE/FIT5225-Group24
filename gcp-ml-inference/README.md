# EcoLens ML Inference Service

GCP serverless service responsible for wildlife inference, Firestore persistence, tag management, file deletion, subscription management, detection progress tracking, and SNS notification triggering.

## Architecture

```text
AWS Lambda
  -> POST processed S3 file information
  -> GCP Cloud Function
  -> Download AI-ready images or video frames from S3
  -> Load MegaDetector and species classifier from GCS
  -> Detect and classify wildlife
  -> Write results to Firestore
  -> Update detection progress
  -> Publish AWS SNS notification
Technology
Google Cloud Functions Gen 2
Google Cloud Storage
Google Firestore REST API
AWS S3
AWS SNS
MegaDetector mdv5a.pt
Species classifier model.pt
Python 3.10
Project Files
.
├── main.py
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore
Model files are stored in GCS and must not be committed:

gs://<MODEL_BUCKET>/mdv5a.pt
gs://<MODEL_BUCKET>/model.pt
gs://<MODEL_BUCKET>/labels.txt
API Endpoint
Base URL:

https://australia-southeast1-fit5225-a2-aussie-ecolens.cloudfunctions.net/process-file
All non-OPTIONS requests require:

Content-Type: application/json
X-Shared-Secret: <SHARED_SECRET>
The function handles browser CORS preflight requests and returns CORS headers for all API responses.

Inference API
POST /inference
Request from AWS Lambda:

{
  "fileKey": "raw/example.jpg",
  "ai_ready_uris": [
    "s3://bucket/ai-ready/example.jpg"
  ],
  "thumbnail_uri": "s3://bucket/thumb/example.jpg",
  "sha256": "file-checksum",
  "user_id": "user@example.com"
}
Response:

{
  "file_id": "generated-file-id",
  "file_key": "raw/example.jpg",
  "status": "processed",
  "tags": {
    "dingo": 1
  },
  "total_frame_count": 1,
  "processed_frame_count": 1,
  "firestore_collection": "media",
  "firestore_doc_id": "generated-file-id"
}
If file_id is not provided by the caller, it is generated as:

SHA256(fileKey)
Detection Status API
GET /detection-status/{file_id}
Returns the current processing status for an image or video.

{
  "file_id": "generated-file-id",
  "status": "processing",
  "progress": 30,
  "stage": "detecting",
  "error": null
}
Progress stages:

Progress	Stage
0	queued
10	downloading
30	detecting
80	classifying
90	saving
100	completed
Modify Tags API
POST /tags/modify
{
  "urls": ["s3://bucket/raw/example.jpg"],
  "tags": ["kangaroo"],
  "operation": 1
}
Operations:

1: add tags
0: remove tags
Manual tags are stored in manual_tags, and all_tags is updated as the deduplicated union of auto_tags and manual_tags.

Delete Files API
POST /files/delete
{
  "urls": ["s3://bucket/raw/example.jpg"]
}
Deletes matching Firestore records and associated S3 objects when accessible.

Subscription APIs
Legacy full replacement endpoint:

POST /subscribe
{
  "user_id": "user@example.com",
  "email": "user@example.com",
  "tags": ["dingo", "kangaroo"]
}
Incremental subscription endpoints:

GET /subscriptions?userId={email}
POST /subscriptions
DELETE /subscriptions/{tag}?userId={email}
Add one subscribed tag:

{
  "tag": "dingo",
  "userId": "user@example.com",
  "email": "user@example.com"
}
Stores notification preferences in Firestore.

Firestore Schema
media/{file_id}
{
  "file_id": "string",
  "file_key": "string | null",
  "user_id": "string | null",
  "file_type": "image | video",
  "file_url": "string",
  "thumbnail_url": "string | null",
  "checksum": "string | null",
  "ai_ready_uris": ["s3://..."],
  "total_frame_count": 20,
  "processed_frame_count": 20,
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
subscriptions/{user_id}
{
  "user_id": "user@example.com",
  "email": "user@example.com",
  "tags": ["dingo", "kangaroo"],
  "status": "active",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
detection_status/{file_id}
{
  "file_id": "string",
  "status": "processing | processed | failed",
  "progress": 0,
  "stage": "queued | downloading | detecting | classifying | saving | completed | failed",
  "error": "string | null",
  "updated_at": "timestamp"
}
Environment Variables
See .env.example.

MAX_VIDEO_FRAMES controls the maximum number of AI-ready video frames processed per request. The current default is 20.

Never commit real credentials or secrets.

Deployment
gcloud functions deploy process-file \
  --gen2 \
  --runtime=python310 \
  --trigger-http \
  --allow-unauthenticated \
  --region=australia-southeast1 \
  --source=. \
  --entry-point=process_file \
  --memory=6Gi \
  --cpu=2 \
  --timeout=540s \
  --max-instances=2 \
  --set-env-vars=PROJECT_ID=<PROJECT_ID>,AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID>,AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY>,AWS_REGION=ap-southeast-2,SHARED_SECRET=<SHARED_SECRET>,SNS_TOPIC_ARN=<SNS_TOPIC_ARN>,MODEL_BUCKET=<MODEL_BUCKET>,MD_MODEL_KEY=mdv5a.pt,CLASSIFIER_MODEL_KEY=model.pt,LABELS_KEY=labels.txt,MAX_VIDEO_FRAMES=20
For production, credentials and secrets should be stored using Secret Manager rather than plain environment variables.

## Tag-based SNS Notifications

After inference, the function publishes one SNS message containing all detected species.

The `species` message attribute uses `String.Array`:

```json
{
  "species": {
    "DataType": "String.Array",
    "StringValue": "[\"cattle\", \"human\"]"
  }
}
SNS subscriptions use message-attribute filter policies:

{
  "species": ["cattle", "human"]
}
Each matching subscription receives at most one email per processed file.

## Runtime Resources
Setting	Value
Memory	6Gi
CPU	2
Maximum instances	2
Timeout	540s
Maximum video frames	20
The second instance can serve detection-status requests while another instance performs ML inference.
