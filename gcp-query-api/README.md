# GCP Query API

HTTP Cloud Function skeleton for member D. It is ready for frontend integration, but the Firestore collection name and field names must be confirmed by members B/C before production use.

## Endpoints

```text
GET    /query?type=all
GET    /query?type=tag&value=invasive
GET    /query?type=species&value=Felis%20catus
GET    /query?type=count&minCount=2&maxCount=5
GET    /query?type=thumbnail&value=thumbnail-key-or-file-id
GET    /query?type=file&value=file-key-or-file-id
POST   /files/{fileId}/tags
POST   /files/tags:batchAdd
DELETE /files/{fileId}
```

The frontend expects records in this shape:

```json
{
  "fileId": "img-cat-002",
  "fileName": "Felis_catus_2.JPG",
  "fileKey": "uploads/Felis_catus_2.JPG",
  "imageUrl": "https://...",
  "thumbnailUrl": "https://...",
  "species": "Felis catus",
  "commonName": "domestic cat",
  "confidence": 0.89,
  "count": 1,
  "tags": ["invasive", "night"],
  "uploadedAt": "2026-06-03T07:42:00Z"
}
```

## Request Bodies

Single tag update:

```http
POST /files/{fileId}/tags
Content-Type: application/json

{
  "tags": ["reviewed", "demo"]
}
```

Batch tag update:

```http
POST /files/tags:batchAdd
Content-Type: application/json

{
  "fileIds": ["img-cat-002", "img-boar-003"],
  "tags": ["reviewed"]
}
```

## Local Run

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run locally:

```bash
functions-framework --target=query_api --debug --port=8080
```

Then point the frontend to it:

```env
VITE_QUERY_API_URL=http://localhost:8080
VITE_USE_MOCK_QUERY=false
```

## Deploy

Example deployment command:

```bash
gcloud functions deploy query-api \
  --gen2 \
  --runtime=python312 \
  --region=australia-southeast1 \
  --source=. \
  --entry-point=query_api \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars=DETECTIONS_COLLECTION=detections,ALLOWED_ORIGIN=https://YOUR_FRONTEND_DOMAIN
```

Use authenticated invocation instead of `--allow-unauthenticated` if the team decides to protect the endpoint at GCP IAM/API Gateway level.

## What Members B/C Must Confirm

```text
Firestore collection name
Document id strategy
Exact field names for file id, file key, thumbnail URL/key, species, confidence, count, tags, created_at
Whether deleting S3 objects is handled here with boto3 or by an AWS Lambda
Whether this API must validate the Cognito JWT
```
