# Lambda ① — Upload API 

Pairs with `frontend/src/api/upload.js`. Deploy behind **API Gateway** 

## Routes

| Method | Path | Auth |
|--------|------|------|
| POST | `/requestUploadFile` | Cognito Bearer |
| GET | `/results/{fileKey}` | Cognito Bearer |
| POST | `/internal/uploads/{fileKey}/status` | Internal  |
| POST | `/internal/uploads/{fileKey}/results` | Internal  |

## AWS deploy checklist

1. Create Lambda, runtime Python 3.12, handler `handler.lambda_handler`
2. Environment variables (see `.env.example` in this folder)
3. IAM: `s3:PutObject` on `raw/*` (presign only needs permission on bucket/key)
4. API Gateway HTTP API → integrate routes to this Lambda
5. Member A: Cognito authorizer on public routes

## Pair with Lambda ②

`lambda/process_upload` — S3 trigger for thumbnails/frames.  
Set `UPLOAD_API_URL` on **process_upload** to API Gateway base URL so it can call `/internal/uploads/.../status`.
