#!/usr/bin/env bash
# Copy the DAG files into a clone of the deployment repository, commit, and publish.
# usage: publish_dags.sh <source_repo_dir> <clone_dir> <direct|pr> <base_branch> <source_sha>
#   direct: push HEAD to <base_branch> (one rebase retry; other teams push there too)
#   pr:     push the fixed branch sync/<DAG_SLUG> (updated per run) and open (or reuse) a PR
#           into <base_branch>
# Nothing is committed, pushed or opened when the DAG files have no diff against <base_branch>,
# and in pr mode also not when an open PR's branch already holds exactly these files.
# env:    DAG_SLUG, DAG_EXECUTOR, DAG_UTILS (required), DAG_DEST_DIR (default airflow/dags),
#         SOURCE_REPO (default: the source repository name), GH_BIN, GIT_USER_NAME, GIT_USER_EMAIL
set -euo pipefail

SRC=${1:?usage: publish_dags.sh <source_repo_dir> <clone_dir> <direct|pr> <base_branch> <source_sha>}
CLONE=${2:?clone dir}
MODE=${3:?direct or pr}
BASE=${4:?base branch}
SHA=${5:?source sha}
case "${MODE}" in direct | pr) ;; *) echo "mode must be direct or pr" >&2; exit 2 ;; esac

SLUG=${DAG_SLUG:?set DAG_SLUG (short kebab-case name of the DAG)}
EXECUTOR=${DAG_EXECUTOR:?set DAG_EXECUTOR}
UTILS=${DAG_UTILS:?set DAG_UTILS}
DEST_DIR=${DAG_DEST_DIR:-airflow/dags}
[[ "${SLUG}" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "bad DAG_SLUG: ${SLUG}" >&2; exit 2; }

SHORT=${SHA:0:7}
GH=${GH_BIN:-gh}
HERE=$(cd "$(dirname "$0")" && pwd)
GITHUB_REPOSITORY=${GITHUB_REPOSITORY:-}
SOURCE_REPO=${SOURCE_REPO:-${GITHUB_REPOSITORY##*/}}
SOURCE_REPO=${SOURCE_REPO:-source-repo}

cd "${CLONE}"
git config user.name "${GIT_USER_NAME:-${SLUG}-sync}"
git config user.email "${GIT_USER_EMAIL:-noreply@users.noreply.github.com}"
git checkout -q "${BASE}"
if [ "${MODE}" = "pr" ]; then
  BRANCH="sync/${SLUG}"
  git checkout -q -B "${BRANCH}"
fi

bash "${HERE}/sync_dags.sh" "${SRC}" "${CLONE}"
git add -A -- "${DEST_DIR}/${EXECUTOR}" "${DEST_DIR}/${UTILS}"
if git diff --cached --quiet; then
  echo "No changes to publish (${BASE} already has the DAG from ${SHORT})"
  exit 0
fi

if [ "${MODE}" = "pr" ]; then
  # An open PR whose branch already holds exactly these files needs no new commit: a
  # force-push would only rewrite the commit (new SHA in the message) under the reviewer.
  open_pr=$("${GH}" pr list --head "${BRANCH}" --base "${BASE}" --state open --json number --jq '.[0].number // empty')
  if [ -n "${open_pr}" ] && git fetch -q origin "+refs/heads/${BRANCH}:refs/remotes/origin/${BRANCH}" 2> /dev/null \
    && git diff --cached --quiet "origin/${BRANCH}" -- "${DEST_DIR}/${EXECUTOR}" "${DEST_DIR}/${UTILS}"; then
    echo "No changes to publish (PR #${open_pr} already has these DAG files; ${SHORT} adds nothing)"
    exit 0
  fi
fi
echo "Files copied:"
git diff --cached --name-status
git commit -q -m "chore(airflow): sync ${SLUG} DAG from ${SOURCE_REPO}@${SHORT}"

if [ "${MODE}" = "direct" ]; then
  for attempt in 1 2; do
    if git push -q origin "HEAD:${BASE}"; then
      echo "Pushed ${SHORT} to ${BASE}"
      exit 0
    fi
    [ "${attempt}" = "2" ] && { echo "push to ${BASE} failed twice" >&2; exit 5; }
    git pull -q --rebase origin "${BASE}"
  done
fi

# A fresh clone has no tracking ref for the bot branch, so name the expected remote tip
# explicitly (empty = the branch must not exist yet).
remote_tip=$(git ls-remote origin "refs/heads/${BRANCH}" | cut -f1)
git push -q --force-with-lease="${BRANCH}:${remote_tip}" origin "${BRANCH}"
existing=$("${GH}" pr list --head "${BRANCH}" --base "${BASE}" --state open --json number --jq '.[0].number // empty')
if [ -z "${existing}" ]; then
  "${GH}" pr create --base "${BASE}" --head "${BRANCH}" \
    --title "chore(airflow): sync ${SLUG} DAG (${SHORT})" \
    --body "Automated sync of the ${SLUG} DAG from ${SOURCE_REPO}@${SHA}. Review the diff, then merge."
else
  echo "PR #${existing} is already open for ${BRANCH}; branch updated"
fi
