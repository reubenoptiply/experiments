# Deploy to Google Cloud Run

## Prerequisites

- Google Cloud project with billing enabled.
- `gcloud` CLI installed and logged in: `gcloud auth login`, `gcloud config set project YOUR_PROJECT_ID`.
- Docker (optional; you can use Cloud Build and skip local Docker).
- PostgreSQL reachable from Cloud Run (see "Database connectivity" below).

## 1. Enable APIs and create image registry

```bash
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

Create an Artifact Registry repo (replace `REGION` with your region, e.g. `europe-west1`):

```bash
gcloud artifacts repositories create demo-simulator --repository-format=docker --location=REGION
```

## 2. Build and push the image

**Option A – Build in Cloud (recommended):**

From the repository root:

```bash
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/demo-simulator/demo-account-simulator:latest demo-account-simulator/
```

Or from inside `demo-account-simulator`:

```bash
cd demo-account-simulator
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/demo-simulator/demo-account-simulator:latest .
```

**Option B – Build locally and push:**

```bash
docker build -t REGION-docker.pkg.dev/PROJECT_ID/demo-simulator/demo-account-simulator:latest demo-account-simulator/
gcloud auth configure-docker REGION-docker.pkg.dev
docker push REGION-docker.pkg.dev/PROJECT_ID/demo-simulator/demo-account-simulator:latest
```

## 3. Deploy to Cloud Run

Set `DATABASE_URL` to your PostgreSQL connection string. For a first run you can pass it as an env var (use Secret Manager in production):

```bash
gcloud run deploy demo-account-simulator \
  --image REGION-docker.pkg.dev/PROJECT_ID/demo-simulator/demo-account-simulator:latest \
  --region REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME" \
  --set-env-vars "FAIL_FAST_NO_DB=1"
```

- Omit `--allow-unauthenticated` to require authentication (e.g. for Retool with a service account).
- To use Secret Manager: create secret `DATABASE_URL`, then use `--set-secrets=DATABASE_URL=DATABASE_URL:latest` and grant the Cloud Run service account access to the secret.

The command prints the **service URL** (e.g. `https://demo-account-simulator-xxx.run.app`). Use this as the base URL for Retool (see [RETOOL.md](RETOOL.md)).

## 4. Database connectivity

- **PostgreSQL outside GCP:** If the DB is on the public internet, set `DATABASE_URL` to that URL. If the DB is IP-allowlisted, use a VPC connector with static egress or another way to get a fixed egress IP.
- **Cloud SQL (PostgreSQL):** Use the Cloud SQL Auth Proxy sidecar or connect via private IP. For private IP, attach a VPC connector to the Cloud Run service and set `DATABASE_URL` to the Cloud SQL private IP. Grant the Cloud Run service account `cloudsql.client` if using the proxy.

## 5. Verify

- `https://YOUR_SERVICE_URL/` → `{"status":"active","shop":1380}`
- `https://YOUR_SERVICE_URL/health` → 200 and `{"status":"healthy"}` when DB is reachable; 503 otherwise.
- Test `POST /simulate` and `POST /maintain` from Retool or curl.
