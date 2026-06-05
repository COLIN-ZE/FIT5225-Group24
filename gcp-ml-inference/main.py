import gc
import hashlib
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import boto3
import functions_framework
import google.auth
from flask import jsonify
from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage


gcs_client = storage.Client()

credentials, project_id = google.auth.default(
    scopes=[
        "https://www.googleapis.com/auth/datastore",
        "https://www.googleapis.com/auth/cloud-platform",
    ]
)
firestore_session = AuthorizedSession(credentials)
PROJECT_ID = os.environ.get("PROJECT_ID") or project_id

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SHARED_SECRET = os.environ.get("SHARED_SECRET", "")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

MODEL_BUCKET = os.environ.get("MODEL_BUCKET", "")
MD_MODEL_KEY = os.environ.get("MD_MODEL_KEY", "mdv5a.pt")
CLASSIFIER_MODEL_KEY = os.environ.get("CLASSIFIER_MODEL_KEY", "model.pt")
LABELS_KEY = os.environ.get("LABELS_KEY", "labels.txt")
MAX_VIDEO_FRAMES = int(os.environ.get("MAX_VIDEO_FRAMES", "20"))

MODEL_DIR = Path("/tmp/ecolens_models")
MD_MODEL_PATH = MODEL_DIR / "mdv5a.pt"
CLASSIFIER_MODEL_PATH = MODEL_DIR / "model.pt"
LABELS_PATH = MODEL_DIR / "labels.txt"

_classifier_model = None
_label_rows = None


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=AWS_REGION,
    )


def get_sns_client():
    return boto3.client(
        "sns",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=AWS_REGION,
    )


def _json_error(message, status=400, **extra):
    body = {"error": message}
    body.update(extra)
    return jsonify(body), status


def _check_secret(request):
    if not SHARED_SECRET:
        return True
    return request.headers.get("X-Shared-Secret") == SHARED_SECRET


def _normalised_path(request):
    path = request.path.rstrip("/") or "/"
    if path.startswith("/process-file"):
        path = path[len("/process-file"):] or "/"
    return path


def _get_payload(request):
    payload = request.get_json(silent=True)
    if not payload:
        raise ValueError("Missing JSON body")
    return payload


def download_gcs_file(key, destination):
    if not MODEL_BUCKET:
        raise RuntimeError("MODEL_BUCKET environment variable is not set")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return

    bucket = gcs_client.bucket(MODEL_BUCKET)
    blob = bucket.blob(key)
    blob.download_to_filename(str(destination))


def ensure_model_files():
    download_gcs_file(MD_MODEL_KEY, MD_MODEL_PATH)
    download_gcs_file(CLASSIFIER_MODEL_KEY, CLASSIFIER_MODEL_PATH)
    download_gcs_file(LABELS_KEY, LABELS_PATH)


def load_labels():
    global _label_rows
    if _label_rows is not None:
        return _label_rows

    ensure_model_files()
    rows = []

    with open(LABELS_PATH, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split(";")
            if len(parts) < 7:
                continue

            genus = parts[4]
            species = parts[5]
            common_name = parts[6] or f"{genus} {species}"
            scientific_name = f"{genus}_{species}"

            rows.append({
                "scientific_name": scientific_name,
                "common_name": common_name,
            })

    _label_rows = rows
    return _label_rows


def get_classifier_model():
    import torch

    global _classifier_model
    if _classifier_model is not None:
        return _classifier_model

    ensure_model_files()

    model = torch.load(
        CLASSIFIER_MODEL_PATH,
        map_location="cpu",
        weights_only=False,
    )
    model.eval()
    model.to("cpu")

    _classifier_model = model
    return _classifier_model


def parse_s3_url(s3_url):
    parsed = urlparse(s3_url)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
        raise ValueError("URL must be a valid s3://bucket/key URL")
    return parsed.netloc, parsed.path.lstrip("/")


def download_s3_file(s3_url, destination):
    bucket, key = parse_s3_url(s3_url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    get_s3_client().download_file(bucket, key, str(destination))
    return destination


def delete_s3_url_if_possible(url):
    if not url or not str(url).startswith("s3://"):
        return False

    bucket, key = parse_s3_url(url)
    get_s3_client().delete_object(Bucket=bucket, Key=key)
    return True


def run_megadetector_batch(image_paths):
    from megadetector.detection.run_detector_batch import load_and_run_detector_batch

    ensure_model_files()

    results = load_and_run_detector_batch(
        image_file_names=[str(path) for path in image_paths],
        model_file=str(MD_MODEL_PATH),
        image_size=640,
        batch_size=1,
        n_cores=1,
    )

    gc.collect()
    return results

def classify_crop(crop):
    import numpy as np
    import torch
    import torchvision.transforms as transforms

    labels = load_labels()
    model = get_classifier_model()

    transform = transforms.Compose([
        transforms.Resize((480, 480)),
        transforms.ToTensor(),
    ])

    image = crop.convert("RGB")
    image = transform(image)
    image = image.unsqueeze(0)
    image = image.permute(0, 2, 3, 1)

    with torch.no_grad():
        logits = model(image)
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

    best_idx = int(np.argmax(probs))
    label = labels[best_idx] if best_idx < len(labels) else {
        "scientific_name": f"class_{best_idx}",
        "common_name": f"class_{best_idx}",
    }

    return {
        "species": label["common_name"],
        "scientific_name": label["scientific_name"],
        "confidence": float(probs[best_idx]),
    }


def detect_species_from_images(image_paths, source_uris):
    from PIL import Image

    md_results = run_megadetector_batch(image_paths)

    tags = {}
    classified_detections = []

    for image_path, source_uri, entry in zip(
        image_paths,
        source_uris,
        md_results,
    ):
        detections = entry.get("detections", [])

        with Image.open(image_path) as opened_image:
            image = opened_image.convert("RGB")

        width, height = image.size

        for detection in detections:
            if detection.get("category") != "1":
                continue

            md_confidence = float(detection.get("conf", 0))
            if md_confidence < 0.05:
                continue

            x, y, w, h = detection["bbox"]

            left = int(x * width)
            top = int(y * height)
            right = int((x + w) * width)
            bottom = int((y + h) * height)

            crop = image.crop((left, top, right, bottom)).resize((600, 600))
            result = classify_crop(crop)
            crop.close()

            species = result["species"]
            tags[species] = tags.get(species, 0) + 1

            classified_detections.append({
                "species": species,
                "scientific_name": result["scientific_name"],
                "classification_confidence": result["confidence"],
                "detection_confidence": md_confidence,
                "bbox": detection["bbox"],
                "source_uri": source_uri,
            })

        image.close()
        gc.collect()

    return tags, classified_detections

def firestore_value(value):
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            return {"nullValue": None}
        return {"doubleValue": value}
    if isinstance(value, datetime):
        return {"timestampValue": value.isoformat().replace("+00:00", "Z")}
    if isinstance(value, list):
        return {"arrayValue": {"values": [firestore_value(item) for item in value]}}
    if isinstance(value, dict):
        return {
            "mapValue": {
                "fields": {key: firestore_value(val) for key, val in value.items()}
            }
        }
    return {"stringValue": str(value)}


def firestore_to_python(value):
    if "nullValue" in value:
        return None
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "timestampValue" in value:
        return value["timestampValue"]
    if "stringValue" in value:
        return value["stringValue"]
    if "arrayValue" in value:
        return [firestore_to_python(item) for item in value.get("arrayValue", {}).get("values", [])]
    if "mapValue" in value:
        return {
            key: firestore_to_python(val)
            for key, val in value.get("mapValue", {}).get("fields", {}).items()
        }
    return None


def doc_to_python(doc):
    fields = doc.get("fields", {})
    data = {key: firestore_to_python(value) for key, value in fields.items()}
    data["_name"] = doc.get("name")
    data["_id"] = doc.get("name", "").split("/")[-1]
    return data


def document_url(collection, doc_id):
    return (
        f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/databases/(default)/documents/{collection}/{doc_id}"
    )


def write_document(collection, doc_id, document):
    body = {"fields": {key: firestore_value(value) for key, value in document.items()}}
    response = firestore_session.patch(document_url(collection, doc_id), json=body, timeout=30)
    response.raise_for_status()


def delete_document(collection, doc_id):
    response = firestore_session.delete(document_url(collection, doc_id), timeout=30)
    if response.status_code not in (200, 404):
        response.raise_for_status()


def query_media_by_field(field_name, value):
    url = (
        f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/databases/(default)/documents:runQuery"
    )

    body = {
        "structuredQuery": {
            "from": [{"collectionId": "media"}],
            "where": {
                "fieldFilter": {
                    "field": {"fieldPath": field_name},
                    "op": "EQUAL",
                    "value": firestore_value(value),
                }
            },
        }
    }

    response = firestore_session.post(url, json=body, timeout=30)
    response.raise_for_status()

    docs = []
    for item in response.json():
        if "document" in item:
            docs.append(doc_to_python(item["document"]))
    return docs


def find_media_documents_by_urls(urls):
    seen = {}
    for url in urls:
        for field in ("file_url", "thumbnail_url", "file_key"):
            for doc in query_media_by_field(field, url):
                seen[doc["_id"]] = doc
    return list(seen.values())


def notify_subscribers(tags, file_url, thumbnail_url):
    if not SNS_TOPIC_ARN or not tags:
        return

    message = (
        "New wildlife detected.\n"
        f"Species: {', '.join(tags.keys())}\n"
        f"File URL: {file_url}\n"
        f"Thumbnail URL: {thumbnail_url or 'N/A'}"
    )

    publish_args = {
        "TopicArn": SNS_TOPIC_ARN,
        "Subject": "EcoLens: New wildlife detected",
        "Message": message,
    }

    if SNS_TOPIC_ARN.endswith(".fifo"):
        publish_args["MessageGroupId"] = "ecolens-notifications"
        publish_args["MessageDeduplicationId"] = str(uuid.uuid4())

    get_sns_client().publish(**publish_args)



def update_detection_progress(file_id, status, progress, stage, error=None):
    document = {
        "file_id": file_id,
        "status": status,
        "progress": progress,
        "stage": stage,
        "updated_at": datetime.now(timezone.utc),
    }

    if error is not None:
        document["error"] = str(error)

    write_document("detection_status", file_id, document)


def _handle_detection_status(request, file_id):
    status_doc = get_document("detection_status", file_id)

    if not status_doc:
        return _json_error("Detection status not found", 404)

    return jsonify({
        "file_id": file_id,
        "status": status_doc.get("status"),
        "progress": status_doc.get("progress", 0),
        "stage": status_doc.get("stage"),
        "error": status_doc.get("error"),
    }), 200



def _handle_inference(request):
    payload = _get_payload(request)

    file_key = payload.get("fileKey") or payload.get("file_key")
    ai_ready_uris = payload.get("ai_ready_uris", [])
    thumbnail_url = (
        payload.get("thumbnail_uri")
        or payload.get("thumbnail_url")
        or payload.get("thumb_url")
    )

    legacy_file_url = payload.get("file_url")
    file_url = legacy_file_url or file_key

    if isinstance(ai_ready_uris, str):
        ai_ready_uris = [ai_ready_uris]

    if not ai_ready_uris and legacy_file_url:
        ai_ready_uris = [legacy_file_url]

    total_frame_count = len(ai_ready_uris)
    if total_frame_count > MAX_VIDEO_FRAMES:
        ai_ready_uris = ai_ready_uris[:MAX_VIDEO_FRAMES]
    processed_frame_count = len(ai_ready_uris)

    if not file_key and not legacy_file_url:
        return _json_error("fileKey or file_url is required", 400)

    if not ai_ready_uris:
        return _json_error("ai_ready_uris or file_url is required", 400)

    file_id = payload.get("file_id")
    if not file_id:
        source_id = file_key or legacy_file_url
        file_id = hashlib.sha256(source_id.encode("utf-8")).hexdigest()

    checksum = payload.get("checksum") or payload.get("sha256")
    user_id = payload.get("user_id")
    file_type = payload.get("file_type")
    if not file_type:
        file_type = "video" if len(ai_ready_uris) > 1 else "image"

    try:
        update_detection_progress(file_id, "processing", 0, "queued")
        update_detection_progress(file_id, "processing", 10, "downloading")

        local_paths = []

        for index, uri in enumerate(ai_ready_uris):
            local_path = Path(f"/tmp/{file_id}_{index}.jpg")
            download_s3_file(uri, local_path)
            local_paths.append(local_path)

        # Load MegaDetector once for all image/video frames.
        update_detection_progress(file_id, "processing", 30, "detecting")

        tags, all_detections = detect_species_from_images(
            local_paths,
            ai_ready_uris,
        )

        update_detection_progress(file_id, "processing", 80, "classifying")

        for local_path in local_paths:
            local_path.unlink(missing_ok=True)

        gc.collect()

        now = datetime.now(timezone.utc)

        document = {
            "file_id": file_id,
            "file_key": file_key,
            "user_id": user_id,
            "file_type": file_type,
            "file_url": file_url,
            "thumbnail_url": thumbnail_url,
            "checksum": checksum,
            "ai_ready_uris": ai_ready_uris,
            "total_frame_count": total_frame_count,
            "processed_frame_count": processed_frame_count,
            "tags": tags,
            "auto_tags": list(tags.keys()),
            "manual_tags": [],
            "all_tags": list(tags.keys()),
            "detections": all_detections,
            "status": "processed",
            "created_at": now,
            "updated_at": now,
        }

        update_detection_progress(file_id, "processing", 90, "saving")
        write_document("media", file_id, document)
        update_detection_progress(file_id, "processed", 100, "completed")

        try:
            notify_subscribers(tags, file_url, thumbnail_url)
        except Exception as notification_error:
            print(f"SNS notification failed: {notification_error}")

        return jsonify({
            "file_id": file_id,
            "file_key": file_key,
            "status": "processed",
            "tags": tags,
            "firestore_collection": "media",
            "firestore_doc_id": file_id,
        }), 200

    except Exception as error:
        try:
            update_detection_progress(
                file_id,
                "failed",
                100,
                "failed",
                error=str(error),
            )
        except Exception as progress_error:
            print(f"Failed to save detection progress: {progress_error}")

        write_document("media", file_id, {
            "file_id": file_id,
            "file_key": file_key,
            "user_id": user_id,
            "file_type": file_type,
            "file_url": file_url,
            "thumbnail_url": thumbnail_url,
            "checksum": checksum,
            "ai_ready_uris": ai_ready_uris,
            "status": "failed",
            "error": str(error),
            "updated_at": datetime.now(timezone.utc),
        })

        return jsonify({
            "file_id": file_id,
            "file_key": file_key,
            "status": "failed",
            "error": str(error),
        }), 500


def _handle_modify_tags(request):
    payload = _get_payload(request)

    urls = payload.get("urls", [])
    tags_to_modify = payload.get("tags", [])
    operation = payload.get("operation")

    if not urls or not isinstance(urls, list):
        return _json_error("urls must be a non-empty list", 400)
    if not tags_to_modify or not isinstance(tags_to_modify, list):
        return _json_error("tags must be a non-empty list", 400)
    if operation not in (0, 1):
        return _json_error("operation must be 1 for add or 0 for remove", 400)

    docs = find_media_documents_by_urls(urls)
    now = datetime.now(timezone.utc)
    updated = []

    for doc in docs:
        doc_id = doc["_id"]

        auto_tags = set(doc.get("auto_tags", []))
        manual_tags = set(doc.get("manual_tags", []))
        tags_map = dict(doc.get("tags", {}) or {})

        for tag in tags_to_modify:
            if operation == 1:
                manual_tags.add(tag)
                tags_map[tag] = max(int(tags_map.get(tag, 0)), 1)
            else:
                manual_tags.discard(tag)
                if tag not in auto_tags:
                    tags_map.pop(tag, None)

        all_tags = sorted(auto_tags | manual_tags)

        doc.update({
            "manual_tags": sorted(manual_tags),
            "all_tags": all_tags,
            "tags": tags_map,
            "updated_at": now,
        })

        clean_doc = {key: value for key, value in doc.items() if not key.startswith("_")}
        write_document("media", doc_id, clean_doc)
        updated.append(doc_id)

    return jsonify({
        "status": "updated",
        "updated_count": len(updated),
        "updated_doc_ids": updated,
    }), 200


def _handle_delete_files(request):
    payload = _get_payload(request)

    urls = payload.get("urls", [])
    if not urls or not isinstance(urls, list):
        return _json_error("urls must be a non-empty list", 400)

    docs = find_media_documents_by_urls(urls)
    deleted_docs = []
    deleted_storage_urls = []

    for doc in docs:
        storage_urls = [
            doc.get("file_url"),
            doc.get("thumbnail_url"),
            *(doc.get("frame_urls", []) or []),
            *(doc.get("ai_ready_uris", []) or []),
        ]

        for url in storage_urls:
            if delete_s3_url_if_possible(url):
                deleted_storage_urls.append(url)

        delete_document("media", doc["_id"])
        deleted_docs.append(doc["_id"])

    return jsonify({
        "status": "deleted",
        "deleted_doc_count": len(deleted_docs),
        "deleted_doc_ids": deleted_docs,
        "deleted_storage_urls": deleted_storage_urls,
    }), 200


def _handle_subscribe(request):
    payload = _get_payload(request)

    user_id = payload.get("user_id") or payload.get("email")
    email = payload.get("email")
    subscribed_tags = payload.get("tags", [])

    if not user_id:
        return _json_error("user_id or email is required", 400)
    if not subscribed_tags or not isinstance(subscribed_tags, list):
        return _json_error("tags must be a non-empty list", 400)

    now = datetime.now(timezone.utc)

    subscription_doc = {
        "user_id": user_id,
        "email": email,
        "tags": sorted(set(subscribed_tags)),
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }

    write_document("subscriptions", user_id.replace("/", "_"), subscription_doc)

    sns_subscription_arn = None
    if email and SNS_TOPIC_ARN and not SNS_TOPIC_ARN.endswith(".fifo"):
        response = get_sns_client().subscribe(
            TopicArn=SNS_TOPIC_ARN,
            Protocol="email",
            Endpoint=email,
            ReturnSubscriptionArn=True,
        )
        sns_subscription_arn = response.get("SubscriptionArn")

    return jsonify({
        "status": "subscribed",
        "user_id": user_id,
        "tags": subscription_doc["tags"],
        "sns_subscription_arn": sns_subscription_arn,
    }), 200



def get_document(collection, doc_id):
    response = firestore_session.get(
        document_url(collection, doc_id),
        timeout=30,
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return doc_to_python(response.json())


def subscription_doc_id(user_id):
    return user_id.replace("/", "_")


def _handle_get_subscriptions(request):
    user_id = request.args.get("userId")

    if not user_id:
        return _json_error("userId is required", 400)

    subscription = get_document(
        "subscriptions",
        subscription_doc_id(user_id),
    )

    if not subscription:
        return jsonify({
            "userId": user_id,
            "tags": [],
            "status": "inactive",
        }), 200

    return jsonify({
        "userId": user_id,
        "email": subscription.get("email"),
        "tags": subscription.get("tags", []),
        "status": subscription.get("status", "active"),
    }), 200


def _handle_add_subscription(request):
    payload = _get_payload(request)

    user_id = payload.get("userId") or payload.get("user_id")
    email = payload.get("email")
    tag = payload.get("tag")

    if not user_id:
        return _json_error("userId is required", 400)

    if not tag or not isinstance(tag, str):
        return _json_error("tag is required", 400)

    tag = tag.strip()
    doc_id = subscription_doc_id(user_id)
    existing = get_document("subscriptions", doc_id)
    tags = set(existing.get("tags", [])) if existing else set()
    tags.add(tag)

    now = datetime.now(timezone.utc)

    write_document("subscriptions", doc_id, {
        "user_id": user_id,
        "email": email or (existing or {}).get("email"),
        "tags": sorted(tags),
        "status": "active",
        "created_at": (existing or {}).get("created_at") or now,
        "updated_at": now,
    })

    return jsonify({
        "status": "subscribed",
        "userId": user_id,
        "tags": sorted(tags),
    }), 200


def _handle_delete_subscription(request, tag):
    user_id = request.args.get("userId")

    if not user_id:
        return _json_error("userId is required", 400)

    tag = unquote(tag).strip()
    doc_id = subscription_doc_id(user_id)
    existing = get_document("subscriptions", doc_id)

    if not existing:
        return _json_error("Subscription not found", 404)

    tags = set(existing.get("tags", []))
    tags.discard(tag)

    if tags:
        write_document("subscriptions", doc_id, {
            "user_id": user_id,
            "email": existing.get("email"),
            "tags": sorted(tags),
            "status": "active",
            "created_at": existing.get("created_at"),
            "updated_at": datetime.now(timezone.utc),
        })
    else:
        delete_document("subscriptions", doc_id)

    return jsonify({
        "status": "unsubscribed",
        "userId": user_id,
        "removedTag": tag,
        "tags": sorted(tags),
    }), 200




CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Shared-Secret",
}


def _add_cors(result):
    if isinstance(result, tuple):
        response = result[0]
        status = result[1] if len(result) > 1 else 200
    else:
        response = result
        status = 200

    for key, value in CORS_HEADERS.items():
        response.headers[key] = value

    return response, status

@functions_framework.http
def process_file(request):
    if request.method == "OPTIONS":
        from flask import Response
        return Response("", status=204, headers=CORS_HEADERS)

    if not _check_secret(request):
        return _add_cors(_json_error("Unauthorized", 401))

    path = _normalised_path(request)

    if path in ("/", "/inference") and request.method == "POST":
        result = _handle_inference(request)
    elif path == "/tags/modify" and request.method == "POST":
        result = _handle_modify_tags(request)
    elif path == "/files/delete" and request.method == "POST":
        result = _handle_delete_files(request)
    elif path == "/subscriptions" and request.method == "GET":
        result = _handle_get_subscriptions(request)
    elif path == "/subscriptions" and request.method == "POST":
        result = _handle_add_subscription(request)
    elif path.startswith("/subscriptions/") and request.method == "DELETE":
        tag = path.removeprefix("/subscriptions/")
        result = _handle_delete_subscription(request, tag)
    elif path.startswith("/detection-status/") and request.method == "GET":
        file_id = path.removeprefix("/detection-status/")
        result = _handle_detection_status(request, file_id)
    elif path == "/subscribe" and request.method == "POST":
        result = _handle_subscribe(request)
    else:
        result = _json_error("Not found", 404, path=path)

    return _add_cors(result)

