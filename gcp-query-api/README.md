# Query API

HTTP Cloud Function for member D. In the final AWS-only integration, the Vue frontend calls A's AWS API Gateway, and AWS API Gateway forwards the protected requests to this Cloud Function.

```text
Vue frontend -> AWS API Gateway + Cognito JWT -> query-api Cloud Function -> Firestore
```

The frontend does not call Firestore directly, and in the final deployment it should not call this Cloud Function directly either.

This version is aligned with member C's Firestore schema:

```text
media/{file_id}
subscriptions/{user_id with "/" replaced by "_"}
```

## Endpoints

```text
GET    /query?type=all
GET    /query?type=tag&value=dingo
GET    /query?type=species&value=dingo
GET    /query?type=count&value=dingo&minCount=2
GET    /query?type=thumbnail&value=https://...
GET    /query?type=file&value=uploads/example.jpg
GET    /tags
GET    /tags?includeCounts=true
POST   /files/{fileId}/tags
POST   /files/tags:batchAdd
DELETE /files/{fileId}
GET    /subscriptions?userId=user@example.com
POST   /subscriptions
DELETE /subscriptions/{tag}?userId=user@example.com
```

The optional GCP API Gateway contract is defined in:

```text
openapi.yaml
```

That file is kept for internal GCP testing only. The assignment/demo entry point should be AWS API Gateway. See [AWS_GATEWAY.md](AWS_GATEWAY.md).

The API only returns media documents where:

```text
status == "processed"
```

## Media Schema

Firestore collection:

```text
media
```

Document id:

```text
file_id
```

Expected document shape:

```json
{
  "file_id": "abc123",
  "file_key": "uploads/abc123.jpg",
  "user_id": "user@example.com",
  "file_type": "image",
  "file_url": "https://...",
  "thumbnail_url": "https://...",
  "checksum": "...",
  "ai_ready_uris": ["s3://bucket/ai-ready/example.jpg"],
  "tags": {
    "dingo": 2,
    "kangaroo": 1
  },
  "auto_tags": ["dingo", "kangaroo"],
  "manual_tags": ["reviewed"],
  "all_tags": ["dingo", "kangaroo", "reviewed"],
  "detections": [
    {
      "species": "dingo",
      "scientific_name": "canis_dingo",
      "classification_confidence": 0.91,
      "detection_confidence": 0.82,
      "bbox": [0, 0, 100, 100],
      "source_uri": "s3://bucket/ai-ready/example.jpg"
    }
  ],
  "status": "processed",
  "created_at": "...",
  "updated_at": "..."
}
```

## Frontend Response Shape

The API normalises Firestore documents to the frontend shape:

```json
{
  "fileId": "abc123",
  "fileName": "abc123.jpg",
  "fileKey": "uploads/abc123.jpg",
  "imageUrl": "https://...",
  "thumbnailUrl": "https://...",
  "species": "canis dingo",
  "commonName": "dingo",
  "confidence": 0.91,
  "count": 3,
  "tags": ["dingo", "kangaroo", "reviewed"],
  "tagCounts": {
    "dingo": 2,
    "kangaroo": 1
  },
  "detections": [],
  "aiReadyUris": [],
  "fileType": "image",
  "uploadedAt": "..."
}
```

`imageUrl` and `thumbnailUrl` are browser-facing fields. If Firestore stores S3
values such as `s3://bucket/thumb/example.jpg` or stable keys such as
`raw/example.jpg`, the query API converts them to temporary HTTPS presigned GET
URLs before returning them to the frontend.

Configure S3 signing with:

```env
AWS_S3_BUCKET=aussie-ecolens-media-storage-2026
AWS_REGION=ap-southeast-2
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_PRESIGNED_URL_TTL=3600
```

Do not commit real AWS credentials. Store them only as Cloud Function
environment variables. The credentials need `s3:GetObject` for `raw/*` and
`thumb/*`.

## Tag Updates

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
  "fileIds": ["abc123", "def456"],
  "tags": ["reviewed"]
}
```

Manual tag updates write both:

```text
manual_tags
all_tags
tags
```

They do not change the ML-generated `auto_tags`. Newly added manual tags are also inserted into the `tags` count map with a default count of `1` when the key is not already present.

## File Deletion

The preferred deletion flow is delegated to member C's endpoint:

```text
D frontend -> D query-api DELETE /files/{fileId}
D query-api looks up the media document by fileId
D query-api -> C POST /files/delete with file_url / thumbnail_url / file_key / ai_ready_uris
C deletes S3 original/thumbnail/ai-ready files
C deletes the Firestore media document
```

Configure:

```env
MEDIA_DELETE_URL=https://...
MEDIA_DELETE_SHARED_SECRET=...
```

The delegated request body sent to C is:

```json
{
  "urls": [
    "s3://bucket/raw/example.jpg",
    "https://...",
    "s3://bucket/ai-ready/example.jpg"
  ]
}
```

If `MEDIA_DELETE_SHARED_SECRET` is set, `main.py` sends it as:

```text
X-Shared-Secret: <secret>
```

Do not commit the real shared secret to GitHub. Set it only as a Cloud Function environment variable.

If `MEDIA_DELETE_URL` is not set, `main.py` falls back to local deletion logic. The final deployment should use C's delete endpoint because C confirmed that no additional B Lambda is needed.

`media/test-001` is suitable for query and manual tag testing, but not for real S3 delete testing because it uses mock S3 URLs.

## Subscriptions Schema

Firestore collection:

```text
subscriptions
```

Document id:

```text
user_id with "/" replaced by "_"
```

Expected document shape:

```json
{
  "user_id": "user@example.com",
  "email": "user@example.com",
  "tags": ["dingo", "kangaroo"],
  "status": "active",
  "created_at": "...",
  "updated_at": "..."
}
```

Create subscription:

```http
POST /subscriptions
Content-Type: application/json

{
  "userId": "user@example.com",
  "email": "user@example.com",
  "tag": "dingo"
}
```

List and delete subscriptions:

```text
GET    /subscriptions?userId=user@example.com
DELETE /subscriptions/dingo?userId=user@example.com
```

## Query Notes

```text
Simple species/tag query uses all_tags.
Tag count query uses tags.<species>.
All tags query deduplicates all_tags and tags map keys.
Thumbnail reverse lookup uses thumbnail_url.
Original image/video preview uses file_url.
Video inference frames use ai_ready_uris.
Only status == "processed" records are returned.
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

Then point the frontend to it for local-only testing:

```env
VITE_QUERY_API_URL=http://localhost:8080
VITE_USE_MOCK_QUERY=false
```

## Deploy

### 1. Deploy the Cloud Function Backend

Deploy the backend function first. AWS API Gateway forwards requests to this function.

```bash
gcloud functions deploy query-api \
  --gen2 \
  --runtime=python312 \
  --region=australia-southeast1 \
  --source=. \
  --entry-point=query_api \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars=DETECTIONS_COLLECTION=media,SUBSCRIPTIONS_COLLECTION=subscriptions,ALLOWED_ORIGIN=https://YOUR_FRONTEND_DOMAIN,MEDIA_DELETE_URL=https://C_DELETE_ENDPOINT
```

Record the deployed function URL. It will look similar to:

```text
https://query-api-xxxxx.australia-southeast1.run.app
```

### 2. Connect It Through AWS API Gateway

Use A's AWS API Gateway as the public entry point:

```text
AWS API Gateway base URL -> https://australia-southeast1-fit5225-a2-aussie-ecolens.cloudfunctions.net/query-api
```

Create these AWS routes and attach the Cognito authorizer to each route:

```text
GET    /query
GET    /tags
POST   /files/{fileId}/tags
POST   /files/tags:batchAdd
DELETE /files/{fileId}
GET    /subscriptions
POST   /subscriptions
DELETE /subscriptions/{tag}
```

The AWS integration must preserve the request path and query string, and should forward:

```text
Authorization
Content-Type
```

For final hardening, set a private `GATEWAY_SHARED_SECRET` environment variable on this Cloud Function and configure AWS API Gateway to inject the same value as:

```text
X-Gateway-Secret: <secret>
```

Do not commit the real secret to GitHub.

The frontend should then use:

```env
VITE_API_URL=https://YOUR_AWS_API_ID.execute-api.ap-southeast-2.amazonaws.com/dev
VITE_QUERY_API_URL=
VITE_USE_MOCK_QUERY=false
```

### 3. Optional GCP Gateway Testing

This is not the final AWS-only path. Use it only if you need to debug the Cloud Function before connecting AWS.

Copy `openapi.yaml` to a temporary file and replace:

```text
QUERY_FUNCTION_URL -> deployed Cloud Function URL
GATEWAY_HOST       -> final gateway host, or leave as a placeholder before the first deploy
```

Example:

```bash
gcloud api-gateway api-configs create query-api-config-v1 \
  --api=query-api \
  --openapi-spec=openapi.yaml \
  --project=YOUR_GCP_PROJECT_ID
```

If the API does not exist yet:

```bash
gcloud api-gateway apis create query-api \
  --project=YOUR_GCP_PROJECT_ID
```

### 4. Create or Update the Optional GCP Gateway

```bash
gcloud api-gateway gateways create query-api-gateway \
  --api=query-api \
  --api-config=query-api-config-v1 \
  --location=australia-southeast1 \
  --project=YOUR_GCP_PROJECT_ID
```

Then get the gateway URL:

```bash
gcloud api-gateway gateways describe query-api-gateway \
  --location=australia-southeast1 \
  --project=YOUR_GCP_PROJECT_ID
```

Use the gateway hostname as the frontend API URL:

```env
VITE_QUERY_API_URL=https://YOUR_GATEWAY_HOST
VITE_USE_MOCK_QUERY=false
```

### 5. Gateway Requirement

For the assignment requirement, the production frontend should use the AWS API Gateway URL, not the direct Cloud Function URL.

```text
Vue frontend -> AWS API Gateway -> query-api Cloud Function -> Firestore
```

For internal integration, AWS Gateway can temporarily use the Cognito authorizer plus C's `X-Shared-Secret` for delete. For final submission, AWS Gateway should validate the Cognito JWT so unauthenticated users cannot access protected endpoints. `GATEWAY_SHARED_SECRET` can additionally prevent direct bypass of AWS Gateway.

## Remaining Integration Decisions

```text
Final AWS API Gateway hostname for VITE_API_URL
Final Cognito authorizer details from A
Final GATEWAY_SHARED_SECRET value configured in both AWS Gateway and Cloud Function
```
