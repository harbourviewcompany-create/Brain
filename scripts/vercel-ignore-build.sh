#!/usr/bin/env bash
set -euo pipefail

ref="${VERCEL_GIT_COMMIT_REF:-}"
current="${VERCEL_GIT_COMMIT_SHA:-HEAD}"
previous="${VERCEL_GIT_PREVIOUS_SHA:-}"

# Vercel ignored-build contract: exit 0 = skip deployment, exit 1 = build.
if [[ "${ref}" != "main" ]]; then
  echo "Skipping Vercel build: branch '${ref:-unknown}' is not main."
  exit 0
fi

# On the first main deployment after enabling this control there may be no
# previous successful deployment SHA. Build conservatively in that case.
if [[ -z "${previous}" ]]; then
  echo "Building main: VERCEL_GIT_PREVIOUS_SHA is unavailable."
  exit 1
fi

if ! git cat-file -e "${previous}^{commit}" 2>/dev/null; then
  echo "Building main: previous deployment commit is not present in checkout."
  exit 1
fi

changed="$(git diff --name-only "${previous}" "${current}" -- || true)"
if grep -Eq '^(api/|apps/api/|apps/observatory/|brain/|pyproject\.toml$|constraints\.txt$|vercel\.json$)' <<<"${changed}"; then
  echo "Building main: runtime-relevant files changed."
  printf '%s\n' "${changed}"
  exit 1
fi

echo "Skipping Vercel build: main commit contains no runtime-relevant changes."
printf '%s\n' "${changed}"
exit 0
