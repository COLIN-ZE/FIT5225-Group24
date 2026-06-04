# Lambda — Member B (AWS)

| Folder | Lambda | Trigger |
|--------|--------|---------|
| `request_upload/` | Upload API + dedup | API Gateway |
| `process_upload/` | Thumbnails + video frames | S3 `raw/` event |

## Local test (no AWS)

```bash
cd lambda/process_upload
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python test_local.py
```

Upload API is tested after deploy, or with `lambda/request_upload/test_local.py` + Cognito token.

## Deploy

See each folder’s `README.md`. Wire `UPLOAD_API_URL` on **process_upload** to your API Gateway URL.
