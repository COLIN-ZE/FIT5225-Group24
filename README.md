# FIT5225-Group24 - AussieEcoLense

AussieEcoLense is a FIT5225 Assignment 2 project for Australian wildlife image and video detection. The system supports user authentication, media upload, image/video preprocessing, AI-based species recognition, result queries, manual tag management, file deletion, and tag-based email notifications.

The project uses a hybrid cloud architecture:

```text
Vue frontend
  -> AWS API Gateway + Cognito
  -> AWS Lambda
  -> Amazon S3
  -> GCP Cloud 
  -> Firestore
  -> Cloud Storgae bucket
  -> AWS SNS email notification
```


## Github repo
https://github.com/COLIN-ZE/FIT5225-Group24

## Main Features

- User registration, login and email verification through Amazon Cognito.
- Automatic SNS email subscription after Cognito user confirmation.
- Image and video upload with frontend SHA-256 hashing and backend S3 presigned URLs.
- Duplicate upload detection to avoid repeated processing.
- Thumbnail generation for images, video frame extraction, and AI-ready media preparation.
- Wildlife detection and classification using MegaDetector and a species classifier.
- Firestore persistence for species, counts, confidence scores, file URLs and tags.
- Query support by all results, tag, species, count, thumbnail and file name.
- Manual tag updates for single files and batches.
- File deletion across S3 and Firestore records.
- Tag-based email subscriptions with SNS filter policy synchronisation.

## Repository Structure

```text
.
|-- frontend/                    Vue 3 + Vite frontend
|-- lambda/
|   |-- request_upload/          Upload request API and presigned URL generation
|   |-- process_upload/          S3 upload processor for thumbnails and AI-ready media
|   |-- update_sns_filter/       SNS subscription filter sync Lambda
|   `-- cognito-post-confirmation/
|                                Cognito post-confirmation SNS subscription Lambda
|-- gcp-ml-inference/            GCP Cloud Function for ML inference and Firestore writes
|-- gcp-query-api/               GCP Cloud Function query/subscription API
|-- test_images/                 Sample wildlife images for testing
|-- AussieEcoLense/              Local model package, ignored by Git
|-- FIT5225 2026 S1 A2.pdf
`-- FIT5225 2026 S1 A2 Marking Rubric.pdf
```

## Module Overview

### Frontend

Location: `frontend/`

The frontend is a Vue 3 + Vite application. It provides authentication, upload, query, result management, tag management, delete actions and subscription screens.

Important files:

```text
frontend/src/api/          API clients
frontend/src/views/        Page views
frontend/src/router/       Vue Router setup
frontend/.env      Frontend environment
```

Run locally:

```bash
cd frontend
npm install
npm run dev
```

### AWS Upload API

Location: `lambda/request_upload/`

This Lambda handles upload requests from the frontend. It verifies Cognito bearer tokens, checks SHA-256 duplicate records, generates S3 presigned PUT URLs, and stores upload metadata.

Main routes:

```text
POST /requestUploadFile
GET  /results/{fileKey}
POST /internal/uploads/{fileKey}/status
POST /internal/uploads/{fileKey}/results
```

See `lambda/request_upload/README.md` for local testing and deployment details.

### AWS Upload Processor

Location: `lambda/process_upload/`

This Lambda is triggered by S3 uploads under the raw prefix. It calculates checksums, detects duplicate uploads, creates thumbnails, standardises images, extracts video frames, uploads processed files back to S3, then calls the GCP ML inference service if `GCP_CALLBACK_URL` is configured.

S3 layout:

```text
raw/        Original frontend uploads
thumb/      UI thumbnails
ai-ready/   Standardised images or video frames for ML
rejected/   Duplicate uploads
```


### GCP ML Inference Service

Location: `gcp-ml-inference/`

This Cloud Function downloads AI-ready S3 media, loads the detection/classification models from Google Cloud Storage, writes results to Firestore, updates detection progress, and publishes tag-based SNS notifications.

Main endpoints:

```text
POST /inference
GET  /detection-status/{file_id}
POST /tags/modify
POST /files/delete
GET  /subscriptions
POST /subscriptions
DELETE /subscriptions/{tag}
```

Required model files are stored in GCS and must not be committed:

```text
gs://<MODEL_BUCKET>/mdv5a.pt
gs://<MODEL_BUCKET>/model.pt
gs://<MODEL_BUCKET>/labels.txt
```

See `gcp-ml-inference/README.md` for schema, environment variables and deployment commands.

### GCP Query API

Location: `gcp-query-api/`

This Cloud Function reads processed Firestore media documents and exposes query, tag, delete and subscription APIs for the frontend. In the final architecture, the frontend should call it through AWS API Gateway, not directly.

Main routes:

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


See `gcp-query-api/README.md` and `gcp-query-api/AWS_GATEWAY.md` for the full API contract and AWS Gateway integration notes.

### SNS Filter Sync Lambda

Location: `lambda/update_sns_filter/`

This Lambda updates the SNS email subscription filter policy after a user changes their subscribed tags in the frontend. It is intended to be deployed behind API Gateway and called by the subscription workflow.

Route:

```text
POST /subscriptions/sync
```

Request body:

```json
{
  "email": "user@example.com",
  "tags": ["dingo", "kangaroo"]
}
```

Required environment variables:

```env
SNS_TOPIC_ARN=
AWS_REGION=ap-southeast-2
CORS_ORIGIN=
```

Required IAM permissions:

```text
sns:ListSubscriptionsByTopic
sns:SetSubscriptionAttributes
```

The Lambda finds the confirmed SNS email subscription for the user and updates its filter policy to:

```json
{
  "species": ["dingo", "kangaroo"]
}
```

### Cognito Post-confirmation Lambda

Location: `lambda/cognito-post-confirmation/`

This Lambda is designed for the Amazon Cognito Post Confirmation trigger. After a user confirms their account, the Lambda reads the user's email address from the Cognito event and subscribes it to the configured SNS topic.

Trigger:

```text
Cognito User Pool -> Post confirmation
```

Handler:

```text
lambda.lambda_handler
```

Required environment variables:

```env
SNS_TOPIC_ARN=
```

Required IAM permissions:

```text
sns:Subscribe
```

The initial SNS filter policy is set to:

```json
{
  "species": ["__none__"]
}
```

This prevents a newly confirmed user from receiving species notifications before they choose subscription tags in the frontend.

## Data Model

The main Firestore collections are:

```text
media/{file_id}
subscriptions/{user_id}
detection_status/{file_id}
```

The `media` documents contain upload metadata, original and thumbnail URLs, AI-ready URIs, detected species, tag counts, manual tags, auto tags, detection boxes and processing status.

The `subscriptions` documents store each user's email and subscribed species tags.

The `detection_status` documents track progress for long-running image/video inference jobs.


## Local Development

Typical local workflow:

```bash
# Frontend
cd frontend
npm install
npm run dev
```

Important production settings:

- API Gateway should protect public routes with Cognito JWT authorisation.
- GCP endpoints should use shared-secret headers when called through AWS Gateway or internal services.
- Secrets should be configured through cloud environment variables or Secret Manager, not committed to Git.
- CORS origins should be restricted to the deployed frontend domain.

## Test Assets

`test_images/` contains sample wildlife images for manual upload and query testing. The filenames include species names such as:

```text
Alectura_lathami
Bos_taurus
Canis_familiaris
Casuarius_casuarius
Felis_catus
Hypsiprymnodon_moschatus
Megapodius_reinwardt
Perameles_nasuta
Sus_scrofa
Uromys_caudimaculatus
```

Assignment files:

- `FIT5225 2026 S1 A2.pdf`
- `FIT5225 2026 S1 A2 Marking Rubric.pdf`


