import os

AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
RAW_PREFIX = os.environ.get("RAW_PREFIX", "raw/").rstrip("/") + "/"

COGNITO_REGION = os.environ.get("COGNITO_REGION", AWS_REGION)
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")

FIRESTORE_PROJECT_ID = os.environ.get("FIRESTORE_PROJECT_ID", "")
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
USE_LOCAL_DB = os.environ.get("USE_LOCAL_DB", "false").lower() in ("1", "true", "yes")

PRESIGN_EXPIRY_SECONDS = int(os.environ.get("PRESIGN_EXPIRY_SECONDS", "3600"))

CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
