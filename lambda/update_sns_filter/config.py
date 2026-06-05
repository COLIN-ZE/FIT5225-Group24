import os

AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "*")
