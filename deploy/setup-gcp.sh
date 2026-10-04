#!/usr/bin/env bash
# Usage: PROJECT_ID=my-project ./deploy/setup-gcp.sh
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-northamerica-northeast1}"
REPO="${REPO:-optiframe}"

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

gcloud artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1 ||
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION"

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
BUILD_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for role in roles/run.admin roles/iam.serviceAccountUser roles/artifactregistry.writer roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${BUILD_SA}" --role="$role" --condition=None >/dev/null
done

# The service runs as its own account with no roles: the default compute account is often a project Editor,
# and a compromised container would get its token from the metadata server.
RUN_SA="optiframe-run@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud iam service-accounts describe "$RUN_SA" >/dev/null 2>&1 ||
  gcloud iam service-accounts create optiframe-run --display-name="OptiFrame Cloud Run runtime"
