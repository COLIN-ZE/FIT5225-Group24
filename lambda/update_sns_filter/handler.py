"""
update_sns_filter — API Gateway → Lambda

Route (add to API Gateway):
  POST /subscriptions/sync

Receives the latest tag list from the frontend after a user subscribes or
unsubscribes, then updates the SNS email subscription filter policy so the
user only receives notifications for their current tags.

Required env vars:
  SNS_TOPIC_ARN   — ARN of the SNS topic (e.g. arn:aws:sns:ap-southeast-2:...:Mytopic)
  AWS_REGION      — defaults to ap-southeast-2
  CORS_ORIGIN     — defaults to *

Required IAM permissions for the Lambda execution role:
  sns:ListSubscriptionsByTopic
  sns:SetSubscriptionAttributes
"""

from __future__ import annotations

import json
from typing import Any

import boto3

from config import AWS_REGION, CORS_ORIGIN, SNS_TOPIC_ARN


# ── helpers ──────────────────────────────────────────────────────────────────

def _http_method(event: dict[str, Any]) -> str:
    if "httpMethod" in event:
        return event["httpMethod"].upper()
    return (
        event.get("requestContext", {})
        .get("http", {})
        .get("method", "GET")
        .upper()
    )


def _path(event: dict[str, Any]) -> str:
    path = event.get("rawPath") or event.get("path") or "/"
    stage = event.get("requestContext", {}).get("stage")
    if stage and path.startswith(f"/{stage}"):
        path = path[len(stage) + 1:] or "/"
    return path


def _body_json(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode("utf-8")
    return json.loads(body) if body else {}


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": CORS_ORIGIN,
            "Access-Control-Allow-Headers": "Authorization,Content-Type",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(payload),
    }


# ── SNS helpers ───────────────────────────────────────────────────────────────

def _get_sns_client():
    return boto3.client("sns", region_name=AWS_REGION)


def _find_subscription_arn(sns_client, email: str) -> str | None:
    """
    Iterates pages of subscriptions on the topic and returns the ARN whose
    endpoint matches the given email. Returns None if not found or still pending.
    """
    paginator = sns_client.get_paginator("list_subscriptions_by_topic")
    for page in paginator.paginate(TopicArn=SNS_TOPIC_ARN):
        for sub in page["Subscriptions"]:
            if (
                sub["Protocol"] == "email"
                and sub["Endpoint"].lower() == email.lower()
                and sub["SubscriptionArn"] != "PendingConfirmation"
            ):
                return sub["SubscriptionArn"]
    return None


def _update_filter_policy(sns_client, subscription_arn: str, tags: list[str]) -> None:
    """
    Sets the filter policy to {"species": [<tags>]}.
    Passing an empty list clears the filter (user receives all messages).
    """
    policy = json.dumps({"species": tags}) if tags else "{}"
    sns_client.set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName="FilterPolicy",
        AttributeValue=policy,
    )


# ── handler ───────────────────────────────────────────────────────────────────

def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = _http_method(event)
    path = _path(event)

    if method == "OPTIONS":
        return _response(200, {"ok": True})

    try:
        if method == "POST" and path == "/subscriptions/sync":
            body = _body_json(event)
            email = (body.get("email") or "").strip().lower()
            tags = body.get("tags") or []

            if not email:
                return _response(400, {"code": 400, "message": "email is required"})
            if not isinstance(tags, list):
                return _response(400, {"code": 400, "message": "tags must be an array"})
            if not SNS_TOPIC_ARN:
                return _response(500, {"code": 500, "message": "SNS_TOPIC_ARN not configured"})

            sns = _get_sns_client()
            subscription_arn = _find_subscription_arn(sns, email)

            if not subscription_arn:
                return _response(404, {
                    "code": 404,
                    "message": f"No confirmed SNS subscription found for {email}",
                })

            _update_filter_policy(sns, subscription_arn, tags)

            return _response(200, {
                "code": 200,
                "message": "Filter policy updated",
                "data": {
                    "subscriptionArn": subscription_arn,
                    "tags": tags,
                },
            })

        return _response(404, {"code": 404, "message": "Not found"})

    except ValueError as exc:
        return _response(400, {"code": 400, "message": str(exc)})
    except Exception as exc:
        print(f"[error] update_sns_filter: {exc}")
        return _response(500, {"code": 500, "message": "Internal server error"})
