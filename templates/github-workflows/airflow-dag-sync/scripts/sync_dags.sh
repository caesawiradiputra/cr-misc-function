#!/usr/bin/env bash
# Copy one DAG's files into a checkout of the Airflow deployment repository.
# usage: sync_dags.sh <source_repo_dir> <deployment_repo_dir>
# env:   DAG_EXECUTOR   file name of the DAG file, e.g. my_dag_executor.py   (required)
#        DAG_UTILS      folder name next to it, e.g. my_dag_utils            (required)
#        DAG_DEST_DIR   DAG folder inside the deployment repo (default airflow/dags)
# Touches exactly: <DAG_DEST_DIR>/<DAG_EXECUTOR> and the folder <DAG_DEST_DIR>/<DAG_UTILS>/
# (replaced as a whole). Nothing else, so other teams' DAGs in the same folder are safe.
set -euo pipefail

SRC=${1:?usage: sync_dags.sh <source_repo_dir> <deployment_repo_dir>}
DEST_REPO=${2:?usage: sync_dags.sh <source_repo_dir> <deployment_repo_dir>}
DEST_REPO=${DEST_REPO%/}

EXECUTOR=${DAG_EXECUTOR:?set DAG_EXECUTOR (file name of the DAG file)}
UTILS=${DAG_UTILS:?set DAG_UTILS (folder name of the DAG helpers)}
DEST_DIR=${DAG_DEST_DIR:-airflow/dags}

# The names reach rm -rf and git add, so only plain names and relative folders are accepted.
[[ "${EXECUTOR}" =~ ^[A-Za-z0-9_]+\.py$ ]] || { echo "bad DAG_EXECUTOR: ${EXECUTOR}" >&2; exit 2; }
[[ "${UTILS}" =~ ^[A-Za-z0-9_]+$ ]] || { echo "bad DAG_UTILS: ${UTILS}" >&2; exit 2; }
[[ "${DEST_DIR}" =~ ^[A-Za-z0-9_]+(/[A-Za-z0-9_-]+)*$ ]] || { echo "bad DAG_DEST_DIR: ${DEST_DIR}" >&2; exit 2; }

DEST_DAGS="${DEST_REPO}/${DEST_DIR}"
UTILS_DEST="${DEST_DAGS}/${UTILS}"

[ -f "${SRC}/dags/${EXECUTOR}" ] || { echo "missing ${SRC}/dags/${EXECUTOR}" >&2; exit 2; }
[ -d "${SRC}/dags/${UTILS}" ] || { echo "missing ${SRC}/dags/${UTILS}" >&2; exit 2; }
[ -d "${DEST_DAGS}" ] || { echo "${DEST_DAGS} does not exist; not a deployment repo checkout" >&2; exit 3; }

# The only directory this script may remove is <repo>/<DAG_DEST_DIR>/<DAG_UTILS>; the name checks
# above guarantee it is a plain folder name below the DAG folder (no "..", no empty name).
rm -rf "${UTILS_DEST}"
mkdir -p "${UTILS_DEST}"
cp -R "${SRC}/dags/${UTILS}/." "${UTILS_DEST}/"
find "${UTILS_DEST}" -name __pycache__ -type d -prune -exec rm -rf {} +
cp "${SRC}/dags/${EXECUTOR}" "${DEST_DAGS}/${EXECUTOR}"
echo "synced ${EXECUTOR} and ${UTILS}/ into ${DEST_DAGS}"
