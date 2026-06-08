import json
import os
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from datetime import date, datetime

from google.cloud import firestore


COLLECTION_NAME = os.getenv("DETECTIONS_COLLECTION", "media")
SUBSCRIPTIONS_COLLECTION = os.getenv("SUBSCRIPTIONS_COLLECTION", "subscriptions")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")
MEDIA_DELETE_URL = os.getenv("MEDIA_DELETE_URL", "")
MEDIA_DELETE_SHARED_SECRET = os.getenv("MEDIA_DELETE_SHARED_SECRET", "")
GATEWAY_SHARED_SECRET = os.getenv("GATEWAY_SHARED_SECRET", "")

FIELD_FILE_ID = os.getenv("FIELD_FILE_ID", "file_id")
FIELD_FILE_KEY = os.getenv("FIELD_FILE_KEY", "file_key")
FIELD_USER_ID = os.getenv("FIELD_USER_ID", "user_id")
FIELD_FILE_TYPE = os.getenv("FIELD_FILE_TYPE", "file_type")
FIELD_FILE_URL = os.getenv("FIELD_FILE_URL", "file_url")
FIELD_THUMBNAIL_URL = os.getenv("FIELD_THUMBNAIL_URL", "thumbnail_url")
FIELD_TAGS = os.getenv("FIELD_TAGS", "tags")
FIELD_AUTO_TAGS = os.getenv("FIELD_AUTO_TAGS", "auto_tags")
FIELD_MANUAL_TAGS = os.getenv("FIELD_MANUAL_TAGS", "manual_tags")
FIELD_ALL_TAGS = os.getenv("FIELD_ALL_TAGS", "all_tags")
FIELD_DETECTIONS = os.getenv("FIELD_DETECTIONS", "detections")
FIELD_AI_READY_URIS = os.getenv("FIELD_AI_READY_URIS", "ai_ready_uris")
FIELD_STATUS = os.getenv("FIELD_STATUS", "status")
FIELD_CREATED_AT = os.getenv("FIELD_CREATED_AT", "created_at")
FIELD_UPDATED_AT = os.getenv("FIELD_UPDATED_AT", "updated_at")

FIELD_SUB_USER_ID = os.getenv("FIELD_SUB_USER_ID", "user_id")
FIELD_SUB_EMAIL = os.getenv("FIELD_SUB_EMAIL", "email")
FIELD_SUB_TAGS = os.getenv("FIELD_SUB_TAGS", "tags")
FIELD_SUB_STATUS = os.getenv("FIELD_SUB_STATUS", "status")
FIELD_SUB_CREATED_AT = os.getenv("FIELD_SUB_CREATED_AT", "created_at")
FIELD_SUB_UPDATED_AT = os.getenv("FIELD_SUB_UPDATED_AT", "updated_at")


db = firestore.Client()


def query_api(request):
    if request.method == "OPTIONS":
        return _response({}, 204)

    try:
        _require_gateway_secret(request)
        path = _normalise_path(request.path)

        if request.method == "GET" and path == "/query":
            return _response({"data": _query_records(request.args)})

        if request.method == "GET" and path == "/tags":
            return _response({"data": _list_tags(request.args)})

        if request.method == "POST" and path.startswith("/files/") and path.endswith("/tags"):
            file_id = path.removeprefix("/files/").removesuffix("/tags").strip("/")
            return _response(_add_tags(file_id, _json_body(request).get("tags", [])))

        if request.method == "POST" and path == "/files/tags:batchAdd":
            body = _json_body(request)
            return _response(_add_tags_batch(body.get("fileIds", []), body.get("tags", [])))

        if request.method == "DELETE" and path.startswith("/files/"):
            file_id = path.removeprefix("/files/").strip("/")
            return _response(_delete_file(file_id))

        if path == "/subscriptions":
            user_id = _current_user_id(request)
            if request.method == "GET":
                return _response({"data": _get_subscriptions(user_id)})
            if request.method == "POST":
                body = _json_body(request)
                return _response(_subscribe(user_id, body.get("email"), body.get("tag")))

        if request.method == "DELETE" and path.startswith("/subscriptions/"):
            user_id = _current_user_id(request)
            tag = path.removeprefix("/subscriptions/").strip("/")
            return _response(_unsubscribe(user_id, tag))

        return _response({"message": "Not found"}, 404)
    except PermissionError as exc:
        return _response({"message": str(exc)}, 403)
    except ValueError as exc:
        return _response({"message": str(exc)}, 400)
    except Exception as exc:
        return _response({"message": str(exc)}, 500)


def _require_gateway_secret(request):
    if not GATEWAY_SHARED_SECRET:
        return
    if request.headers.get("X-Gateway-Secret") != GATEWAY_SHARED_SECRET:
        raise PermissionError("Forbidden")


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
            "Access-Control-Allow-Headers": "Authorization,Content-Type,X-Gateway-Secret",
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


def _subscriptions_collection():
    return db.collection(SUBSCRIPTIONS_COLLECTION)


def _query_records(args):
    query_type = (args.get("type") or "all").lower()
    value = (args.get("value") or "").strip().lower()
    min_count = _optional_int(args.get("minCount"))
    max_count = _optional_int(args.get("maxCount"))

    docs = _collection().where(FIELD_STATUS, "==", "processed").stream()
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
            if _count_matches(record, value, min_count, max_count)
        ]

    if query_type == "thumbnail":
        return [
            record for record in records
            if record["thumbnailUrl"].lower() == value or value in record["fileId"].lower()
        ]

    if query_type == "file":
        return [
            record for record in records
            if value in f"{record['fileName']} {record['fileKey']} {record['fileId']} {record['imageUrl']}".lower()
        ]

    raise ValueError(f"Unsupported query type: {query_type}")


def _list_tags(args):
    include_counts = str(args.get("includeCounts") or "").lower() == "true"
    counts = {}

    docs = _collection().where(FIELD_STATUS, "==", "processed").stream()
    for doc in docs:
        data = doc.to_dict() or {}

        tag_counts = data.get(FIELD_TAGS) or {}
        if isinstance(tag_counts, dict):
            for tag, count in tag_counts.items():
                clean_tag = str(tag).strip().lower()
                if not clean_tag:
                    continue
                counts[clean_tag] = counts.get(clean_tag, 0) + int(count or 0)

        all_tags = data.get(FIELD_ALL_TAGS) or []
        if isinstance(all_tags, list):
            for tag in all_tags:
                clean_tag = str(tag).strip().lower()
                if clean_tag and clean_tag not in counts:
                    counts[clean_tag] = 0

    if include_counts:
        return [{"tag": tag, "count": counts[tag]} for tag in sorted(counts)]
    return sorted(counts)


def _optional_int(value):
    if value in (None, ""):
        return None
    return int(value)


def _normalise_record(doc_id, data):
    file_id = data.get(FIELD_FILE_ID) or doc_id
    tag_counts = data.get(FIELD_TAGS) or {}
    if not isinstance(tag_counts, dict):
        tag_counts = {}
    tag_counts = {
        str(key).strip().lower(): int(value or 0)
        for key, value in tag_counts.items()
        if str(key).strip()
    }

    all_tags = data.get(FIELD_ALL_TAGS) or []
    if not isinstance(all_tags, list):
        all_tags = []

    detections = data.get(FIELD_DETECTIONS) or []
    if not isinstance(detections, list):
        detections = []

    primary = _primary_detection(detections)
    species = primary.get("scientific_name") or primary.get("species") or (all_tags[0] if all_tags else "")
    common_name = primary.get("species") or species
    confidence = primary.get("classification_confidence") or primary.get("detection_confidence") or 0

    return {
        "fileId": file_id,
        "fileName": _filename_from_key(data.get(FIELD_FILE_KEY) or data.get(FIELD_FILE_URL) or file_id),
        "fileKey": data.get(FIELD_FILE_KEY) or "",
        "imageUrl": data.get(FIELD_FILE_URL) or "",
        "thumbnailUrl": data.get(FIELD_THUMBNAIL_URL) or "",
        "species": _display_species(species),
        "commonName": _display_species(common_name),
        "confidence": float(confidence or 0),
        "count": int(sum(int(value or 0) for value in tag_counts.values())),
        "tags": sorted({str(tag) for tag in all_tags}),
        "tagCounts": tag_counts,
        "detections": detections,
        "aiReadyUris": data.get(FIELD_AI_READY_URIS) or [],
        "fileType": data.get(FIELD_FILE_TYPE) or "",
        "uploadedAt": data.get(FIELD_CREATED_AT) or "",
    }


def _count_matches(record, tag, min_count, max_count):
    if tag:
        count = int(record.get("tagCounts", {}).get(tag, 0))
    else:
        count = record["count"]
    return (min_count is None or count >= min_count) and (max_count is None or count <= max_count)


def _primary_detection(detections):
    if not detections:
        return {}
    return max(
        (det for det in detections if isinstance(det, dict)),
        key=lambda det: det.get("classification_confidence") or det.get("detection_confidence") or 0,
        default={},
    )


def _display_species(value):
    return str(value or "").replace("_", " ")


def _filename_from_key(value):
    value = str(value or "")
    if not value:
        return ""
    return value.rstrip("/").split("/")[-1]


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
    _update_manual_tags(doc_ref, clean_tags)
    return {"fileId": file_id, "tags": clean_tags}


def _add_tags_batch(file_ids, tags):
    if not isinstance(file_ids, list) or not file_ids:
        raise ValueError("fileIds must be a non-empty array")

    clean_tags = _clean_tags(tags)
    if not clean_tags:
        raise ValueError("At least one tag is required")

    batch = db.batch()
    for file_id in file_ids:
        doc_ref = _get_doc_ref(file_id)
        snapshot = doc_ref.get()
        data = snapshot.to_dict() or {}
        manual_tags = _merged_tags(data.get(FIELD_MANUAL_TAGS), clean_tags)
        all_tags = _merged_tags(data.get(FIELD_ALL_TAGS), clean_tags)
        tag_counts = _merged_tag_counts(data.get(FIELD_TAGS), clean_tags)
        batch.update(doc_ref, {
            FIELD_TAGS: tag_counts,
            FIELD_MANUAL_TAGS: manual_tags,
            FIELD_ALL_TAGS: all_tags,
            FIELD_UPDATED_AT: firestore.SERVER_TIMESTAMP,
        })
    batch.commit()

    return {"fileIds": file_ids, "tags": clean_tags}


def _delete_file(file_id):
    if MEDIA_DELETE_URL:
        return _delegate_delete_file(file_id)

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


def _update_manual_tags(doc_ref, tags):
    snapshot = doc_ref.get()
    data = snapshot.to_dict() or {}
    doc_ref.update({
        FIELD_TAGS: _merged_tag_counts(data.get(FIELD_TAGS), tags),
        FIELD_MANUAL_TAGS: _merged_tags(data.get(FIELD_MANUAL_TAGS), tags),
        FIELD_ALL_TAGS: _merged_tags(data.get(FIELD_ALL_TAGS), tags),
        FIELD_UPDATED_AT: firestore.SERVER_TIMESTAMP,
    })


def _merged_tags(existing, additions):
    existing = existing if isinstance(existing, list) else []
    return sorted({str(tag).strip().lower() for tag in [*existing, *additions] if str(tag).strip()})


def _merged_tag_counts(existing, additions):
    counts = existing if isinstance(existing, dict) else {}
    merged = {str(key).strip().lower(): int(value or 0) for key, value in counts.items() if str(key).strip()}
    for tag in additions:
        clean = str(tag).strip().lower()
        if clean and clean not in merged:
            merged[clean] = 1
    return merged


def _delegate_delete_file(file_id):
    doc_ref = _get_doc_ref(file_id)
    snapshot = doc_ref.get()
    data = snapshot.to_dict() or {}
    urls = _delete_urls(data)
    if not urls:
        raise ValueError(f"No deletable URLs found for file: {file_id}")

    payload = json.dumps({"urls": urls}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if MEDIA_DELETE_SHARED_SECRET:
        headers["X-Shared-Secret"] = MEDIA_DELETE_SHARED_SECRET

    req = urlrequest.Request(MEDIA_DELETE_URL, data=payload, headers=headers, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=30) as res:
            body = res.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise ValueError(f"Delete endpoint failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise ValueError(f"Delete endpoint unavailable: {exc.reason}") from exc

    if not body:
        return {"fileId": file_id, "deleted": True}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"fileId": file_id, "deleted": True, "message": body}


def _delete_urls(data):
    values = [
        data.get(FIELD_FILE_URL),
        data.get(FIELD_THUMBNAIL_URL),
        data.get(FIELD_FILE_KEY),
        *(data.get(FIELD_AI_READY_URIS) or []),
    ]
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _current_user_id(request):
    body = _json_body(request) if request.method in ("POST", "DELETE") else {}
    user_id = request.args.get("userId") or body.get("userId") or request.headers.get("X-User-Id")
    if not user_id:
        user_id = "demo_user"
    return user_id


def _subscription_doc_id(user_id):
    return str(user_id).replace("/", "_")


def _get_subscriptions(user_id):
    snapshot = _subscriptions_collection().document(_subscription_doc_id(user_id)).get()
    if not snapshot.exists:
        return []
    data = snapshot.to_dict() or {}
    tags = data.get(FIELD_SUB_TAGS) or []
    created_at = data.get(FIELD_SUB_CREATED_AT)
    return [{"tag": tag, "createdAt": created_at} for tag in sorted(tags)]


def _subscribe(user_id, email, tag):
    clean_tag = str(tag or "").strip().lower()
    if not clean_tag:
        raise ValueError("tag is required")

    doc_ref = _subscriptions_collection().document(_subscription_doc_id(user_id))
    snapshot = doc_ref.get()
    if snapshot.exists:
        doc_ref.update({
            FIELD_SUB_EMAIL: email,
            FIELD_SUB_TAGS: firestore.ArrayUnion([clean_tag]),
            FIELD_SUB_STATUS: "active",
            FIELD_SUB_UPDATED_AT: firestore.SERVER_TIMESTAMP,
        })
    else:
        doc_ref.set({
            FIELD_SUB_USER_ID: user_id,
            FIELD_SUB_EMAIL: email,
            FIELD_SUB_TAGS: [clean_tag],
            FIELD_SUB_STATUS: "active",
            FIELD_SUB_CREATED_AT: firestore.SERVER_TIMESTAMP,
            FIELD_SUB_UPDATED_AT: firestore.SERVER_TIMESTAMP,
        })
    return {"tag": clean_tag, "createdAt": datetime.utcnow().isoformat()}


def _unsubscribe(user_id, tag):
    clean_tag = str(tag or "").strip().lower()
    if not clean_tag:
        raise ValueError("tag is required")

    doc_ref = _subscriptions_collection().document(_subscription_doc_id(user_id))
    doc_ref.update({
        FIELD_SUB_TAGS: firestore.ArrayRemove([clean_tag]),
        FIELD_SUB_UPDATED_AT: firestore.SERVER_TIMESTAMP,
    })
    return {"tag": clean_tag, "deleted": True}
