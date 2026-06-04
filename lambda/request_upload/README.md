# Lambda ① — Upload API (Member B)

Pairs with `frontend/src/api/upload.js`. Deploy behind **API Gateway** (Member A adds Cognito JWT authorizer).

## Routes

| Method | Path | Auth |
|--------|------|------|
| POST | `/requestUploadFile` | Cognito Bearer |
| GET | `/results/{fileKey}` | Cognito Bearer |
| POST | `/internal/uploads/{fileKey}/status` | Internal (lock down in prod) |
| POST | `/internal/uploads/{fileKey}/results` | Internal (teammate C) |

## AWS deploy checklist

1. Create Lambda, runtime Python 3.12, handler `handler.lambda_handler`
2. Environment variables (see `.env.example` in this folder)
3. IAM: `s3:PutObject` on `raw/*` (presign only needs permission on bucket/key)
4. API Gateway HTTP API → integrate routes to this Lambda
5. Member A: Cognito authorizer on public routes

## Local test

```bash
cd lambda/request_upload
pip install -r requirements.txt
export USE_LOCAL_DB=true
export LOCAL_DB_PATH=./data/local_db.json
export S3_BUCKET_NAME=your-bucket
export COGNITO_USER_POOL_ID=...
export COGNITO_CLIENT_ID=...
export AWS_REGION=ap-southeast-2
# copy id_token from browser after login:
export TOKEN=eyJ...
python test_local.py request
```

## Pair with Lambda ②

`lambda/process_upload` — S3 trigger for thumbnails/frames.  
Set `UPLOAD_API_URL` on **process_upload** to API Gateway base URL so it can call `/internal/uploads/.../status`.
