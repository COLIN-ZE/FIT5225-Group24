# AWS Gateway Integration

Final public path:

```text
Vue frontend -> AWS API Gateway -> Cognito JWT authorizer -> GCP query-api Cloud Function -> Firestore
```

The GCP Cloud Function URL is the integration backend, not the frontend URL.

## Values Needed

From member A:

```text
AWS API Gateway base URL
Cognito User Pool ID
Cognito App Client ID
Cognito authorizer name or ID
Stage name, usually dev
Allowed frontend origins for CORS
```

From member C:

```text
Firestore project, region, and schema
C delete endpoint URL
C delete endpoint shared secret, stored only in Cloud Function environment variables
A real uploaded file for delete testing
Confirmation that ML keeps manual_tags when reprocessing
Confirmation that SNS notification filtering uses subscriptions.tags
```

## Routes To Add In AWS API Gateway

Attach the Cognito authorizer to every route:

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

All routes should use an HTTP integration or HTTP proxy integration to:

```text
https://australia-southeast1-fit5225-a2-aussie-ecolens.cloudfunctions.net/query-api
```

The integration must preserve:

```text
Path
Query string
Authorization header
Content-Type header
Request body
```

## Internal Gateway Secret

For final hardening, choose a private random value and configure it in two places.

On the GCP Cloud Function:

```text
GATEWAY_SHARED_SECRET=<private value>
```

In AWS API Gateway integration request mapping, append this header:

```text
X-Gateway-Secret: <same private value>
```

Do not store this value in GitHub or in frontend `.env`.

If this variable is empty, the Cloud Function remains callable directly. That is acceptable for early testing, but not ideal for final demo.

## CORS

Allow the frontend origin, for local testing:

```text
http://localhost:5173
```

Allowed methods:

```text
GET, POST, DELETE, OPTIONS
```

Allowed browser headers:

```text
Authorization, Content-Type
```

`X-Gateway-Secret` is injected by AWS Gateway and should not be sent from the browser.

## Frontend Configuration

Use A's AWS API Gateway URL as the single public backend URL:

```env
VITE_API_URL=https://YOUR_API_ID.execute-api.ap-southeast-2.amazonaws.com/dev
VITE_QUERY_API_URL=
VITE_USE_MOCK_QUERY=false
```

`VITE_QUERY_API_URL` must stay empty in the final AWS-only mode. If it is set, the frontend will bypass `VITE_API_URL` for query and subscription calls.

## Validation

After deploying the AWS routes:

1. Login through the frontend so Cognito tokens are available.
2. Open `/query`.
3. Confirm the browser Network tab calls the AWS `execute-api` domain, not a GCP domain.
4. Confirm `GET /query?type=all` returns Firestore `media` records.
5. Add a manual tag and search for it with query type `Tag`.
6. Subscribe to a tag and confirm the `subscriptions` document updates in Firestore.
7. Delete only a real uploaded test file, not `media/test-001`.

Expected auth behavior:

```text
No Authorization header -> 401/403 from AWS Gateway
Valid Cognito JWT -> request reaches query-api
Wrong or missing X-Gateway-Secret after GATEWAY_SHARED_SECRET is enabled -> 403 from query-api
```
