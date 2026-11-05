# ORCID publications — ESPBC (`hedvigsun/perinatallab`, branch `local`)

This package is tailored to the three site source files provided: `_config.yml`,
`_pages/publications.md`, and `Gemfile`. It keeps **Settings > Pages > Deploy
from a branch > local > /(root)**. No switch to "GitHub Actions" as a Pages
publishing source is required.

It was tested locally at the script/unit-test level, but it has **not** been
installed in the GitHub repository or verified against a live ORCID response.

## What it does

* Every day at 05:23 UTC, GitHub Actions reads **all public ORCID work records**
  for the researchers listed in `_data/orcid_researchers.json` (including
  preprints and journal articles, without a year cutoff).
* It groups duplicate records by DOI, or by title/year/work type when appropriate.
  A preprint and the published paper with distinct DOIs remain two records.
* It saves the list in `_data/orcid_publications.json`, commits it to `local`,
  then requests a fresh branch-based GitHub Pages build through the GitHub API.
* On the Publications page, the ORCID list replaces the display of manually
  entered publications **only once imported works exist**. The original
  `_publications/` Markdown files are *not deleted* and remain available.

## Install

1. Back up the `local` branch or create a pull request for review. Add the
   files from this ZIP to the repository, preserving relative paths. The only
   existing file to replace is `_pages/publications.md` (the supplied version
   incorporates the previously provided content). Do NOT replace your existing
   `_config.yml` or `Gemfile`.
2. Edit `_data/orcid_researchers.json` and add **every intended researcher**
   with their verified ORCID iD. The example initially contains only Pol Sole
   Navais. If you run before adding others, the automatic list will only show
   that researcher's publicly listed works.
3. Register Public API credentials from **https://orcid.org/developer-tools**.
   Use an ORCID account with a verified email address and register a Public API
   client. In your GitHub repository open **Settings > Secrets and variables >
   Actions**, and add two **repository secrets**:
     - `ORCID_CLIENT_ID`
     - `ORCID_CLIENT_SECRET`
   Do not paste credentials into a tracked file.
4. Keep **Settings > Pages > Source = Deploy from a branch**, branch **local**,
   folder **/(root)**. This integration is designed to work with your current
   source setting.
5. Commit/push the files to branch **local**. The normal human-authored push
   should publish the page (initially showing the existing manual publications).
6. Go to **Actions > Update ORCID publications > Run workflow** (branch `local`).
   Check that the script fetches ORCID records, commits the JSON, and requests
   a Pages build. Then open **https://espbc.se/publications/** to verify it.

If you do not see a "Run workflow" button, check that this workflow YAML has
been committed to `local`, which is now your default branch.

## Important notes

* A publication is included only if it appears publicly in at least one of
  the selected people's ORCID work lists. Private/limited visibility works
  cannot be retrieved by these Public API credentials.
* The ORCID works summary does not reliably contain a full author citation;
  this display shows title, available year/journal/type/DOI, and the listed
  group members who have the record. For complete author citations, an
  additional metadata-enrichment step (e.g., Crossref) is needed.
* Some article/preprint versions have distinct DOIs and will intentionally
  appear separately. The script deduplicates *within* ORCID imports; the
  page-level fallback prevents duplication with manual entries once import data
  is present.
* A network/API failure aborts without overwriting the existing JSON.
* Automatic scheduled workflows in public repositories can be disabled by
  GitHub after 60 days of no repository activity; re-enable in Actions if needed.
* If `local` is protected against direct bot pushes, modify the workflow to
  raise a pull request and use an approved merge process instead.
* A scheduled job's `GITHUB_TOKEN` commit **does not** by itself start a Pages
  rebuild. This workflow calls `POST /repos/{owner}/{repo}/pages/builds` after
  the push, authenticated with the same job's `GITHUB_TOKEN` and `pages: write`.
  The API documents support for GitHub App installation tokens. If this step
  errors (e.g., a 403 because of repository-level policy), review the Actions
  log and the permissions/publishing settings before choosing a PAT fallback.

## Files

- `_pages/publications.md` — updated copy of your existing page.
- `_includes/orcid-publications.html` — automatic list layout.
- `_data/orcid_researchers.json` — names/ORCID iDs (edit this first).
- `_data/orcid_publications.json` — generated list, initially `[]`.
- `scripts/update_orcid_publications.py` — fetch/normalization/deduplication.
- `.github/workflows/update-orcid-publications.yml` — daily job for `local`.
- `tests/test_orcid_publications.py` — tests for metadata handling.

## Run tests locally

Python 3.11+ is sufficient (the Python script has no third-party dependency):

    python -m unittest discover -s tests -v

To refresh manually, set `ORCID_CLIENT_ID` and `ORCID_CLIENT_SECRET` in your
local environment, then run:

    python scripts/update_orcid_publications.py

Sources: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
         https://docs.github.com/en/rest/pages/pages#request-a-github-pages-build
         https://info.orcid.org/documentation/integration-guide/registering-a-public-api-client/
