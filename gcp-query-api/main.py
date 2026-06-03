import json
import os
from datetime import date, datetime

from google.cloud import firestore


COLLECTION_NAME = os.getenv("DETECTIONS_COLLECTION", "detections")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")

FIELD_FILE_ID = os.getenv("FIELD_FILE_ID", "file_id")
FIELD_FILE_NAME = os.getenv("FIELD_FILE_NAME", "file_name")
FIELD_FILE_KEY = os.getenv("FIELD_FILE_KEY", "file_key")
FIELD_IMAGE_URL = os.getenv("FIELD_IMAGE_URL", "image_url")
FIELD_THUMBNAIL_URL = os.getenv("FIELD_THUMBNAIL_URL", "thumbnail_url")
FIELD_THUMBNAIL_KEY = os.getenv("FIELD_THUMBNAIL_KEY", "thumbnail_key")
FIELD_SPECIES = os.getenv("FIELD_SPECIES", "species")
FIELD_COMMON_NAME = os.getenv("FIELD_COMMON_NAME", "common_name")
FIELD_CONFIDENCE = os.getenv("FIELD_CONFIDENCE", "confidence")
FIELD_COUNT = os.getenv("FIELD_COUNT", "count")
FIELD_TAGS = os.getenv("FIELD_TAGS", "tags")
FIELD_CREATED_AT = os.getenv("FIELD_CREATED_AT", "created_at")


db = firestore.Client()


def query_api(request):
    if request.method == "OPTIONS":
        return _response({}, 204)

    try:
        path = _normalise_path(request.path)

        if request.method == "GET" and path == "/query":
            return _response({"data": _query_records(request.args)})

        if request.method == "POST" and path.startswith("/files/") and path.endswith("/tags"):
            file_id = path.removeprefix("/files/").removesuffix("/tags").strip("/")
            return _response(_add_tags(file_id, _json_body(request).get("tags", [])))

        if request.method == "POST" and path == "/files/tags:batchAdd":
            body = _json_body(request)
            return _response(_add_tags_batch(body.get("fileIds", []), body.get("tags", [])))

        if request.method == "DELETE" and path.startswith("/files/"):
            file_id = path.removeprefix("/files/").strip("/")
            return _response(_delete_file(file_id))

        return _response({"message": "Not found"}, 404)
    except ValueError as exc:
        return _response({"message": str(exc)}, 400)
    except Exception as exc:
        return _response({"message": str(exc)}, 500)


def _normalise_path(path):
    if not path:
        return "/"
    path = path.rstrip("/")
    return path or "/"


def _json_body(request):
    return request.get_json(silent=True) or {}


def _response(payload, status=200):
    body = "" if status == 204 else json.dumps(payload, default=_json_default)
    return (
        body,
        status,
        {
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Authorization,Content-Type",
            "Content-Type": "application/json",
        },
    )


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _collection():
    return db.collection(COLLECTION_NAME)


def _query_records(args):
    query_type = (args.get("type") or "all").lower()
    value = (args.get("value") or "").strip().lower()
    min_count = _optional_int(args.get("minCount"))
    max_count = _optional_int(args.get("maxCount"))

    docs = _collection().stream()
    records = [_normalise_record(doc.id, doc.to_dict() or {}) for doc in docs]

    if query_type == "all" or not value and query_type != "count":
        return records

    if query_type == "tag":
        return [
            record for record in records
            if any(value in tag.lower() for tag in record["tags"])
        ]

    if query_type == "species":
        return [
            record for record in records
            if value in f"{record['species']} {record['commonName']}".lower()
        ]

    if query_type == "count":
        return [
            record for record in records
            if (min_count is None or record["count"] >= min_count)
            and (max_count is None or record["count"] <= max_count)
        ]

    if query_type == "thumbnail":
        return [
            record for record in records
            if value in f"{record['thumbnailUrl']} {record.get('thumbnailKey', '')} {record['fileId']}".lower()
        ]

    if query_type == "file":
        return [
            record for record in records
            if value in f"{record['fileName']} {record['fileKey']} {record['fileId']}".lower()
        ]

    raise ValueError(f"Unsupported query type: {query_type}")


def _optional_int(value):
    if value in (None, ""):
        return None
    return int(value)


def _normalise_record(doc_id, data):
    file_id = data.get(FIELD_FILE_ID) or doc_id
    tags = data.get(FIELD_TAGS) or []
    if not isinstance(tags, list):
        tags = []

    return {
        "fileId": file_id,
        "fileName": data.get(FIELD_FILE_NAME) or data.get("filename") or "",
        "fileKey": data.get(FIELD_FILE_KEY) or "",
        "imageUrl": data.get(FIELD_IMAGE_URL) or data.get("file_url") or "",
        "thumbnailUrl": data.get(FIELD_THUMBNAIL_URL) or data.get("thumb_url") or "",
        "thumbnailKey": data.get(FIELD_THUMBNAIL_KEY) or "",
        "species": data.get(FIELD_SPECIES) or "",
        "commonName": data.get(FIELD_COMMON_NAME) or "",
        "confidence": float(data.get(FIELD_CONFIDENCE) or 0),
        "count": int(data.get(FIELD_COUNT) or 0),
        "tags": tags,
        "uploadedAt": data.get(FIELD_CREATED_AT) or data.get("uploaded_at") or "",
    }


def _get_doc_ref(file_id):
    if not file_id:
        raise ValueError("fileId is required")

    direct_ref = _collection().document(file_id)
    if direct_ref.get().exists:
        return direct_ref

    matches = list(_collection().where(FIELD_FILE_ID, "==", file_id).limit(1).stream())
    if matches:
        return matches[0].reference

    raise ValueError(f"File not found: {file_id}")


def _clean_tags(tags):
    if not isinstance(tags, list):
        raise ValueError("tags must be an array")
    return sorted({str(tag).strip() for tag in tags if str(tag).strip()})


def _add_tags(file_id, tags):
    clean_tags = _clean_tags(tags)
    if not clean_tags:
        raise ValueError("At least one tag is required")

    doc_ref = _get_doc_ref(file_id)
    doc_ref.update({FIELD_TAGS: firestore.ArrayUnion(clean_tags)})
    return {"fileId": file_id, "tags": clean_tags}


def _add_tags_batch(file_ids, tags):
    if not isinstance(file_ids, list) or not file_ids:
        raise ValueError("fileIds must be a non-empty array")

    clean_tags = _clean_tags(tags)
    if not clean_tags:
        raise ValueError("At least one tag is required")

    batch = db.batch()
    for file_id in file_ids:
        batch.update(_get_doc_ref(file_id), {FIELD_TAGS: firestore.ArrayUnion(clean_tags)})
    batch.commit()

    return {"fileIds": file_ids, "tags": clean_tags}


def _delete_file(file_id):
    doc_ref = _get_doc_ref(file_id)
    snapshot = doc_ref.get()
    data = snapshot.to_dict() or {}

    doc_ref.delete()
    _delete_s3_objects(data)

    return {"fileId": file_id, "deleted": True}


def _delete_s3_objects(data):
    bucket = os.getenv("AWS_S3_BUCKET")
    keys = [
        data.get(FIELD_FILE_KEY),
        data.get(FIELD_THUMBNAIL_KEY),
    ]
    keys = [key for key in keys if key]

    if not bucket or not keys:
        return

    try:
        import boto3
    except ImportError:
        return

    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    for key in keys:
        s3.delete_object(Bucket=bucket, Key=key)
