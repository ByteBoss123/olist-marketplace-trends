# Continuous integration

The `Analytics CI` workflow runs on pull requests to main and pushes to main or the review branch.
It installs pinned direct CI dependencies on Python 3.12 and runs `bash scripts/ci.sh`.
A failed command fails the job. Validated outputs are retained as GitHub Actions artifacts for seven days.

To run the same checks locally:

```bash
python -m pip install -r requirements-ci.txt
bash scripts/ci.sh
```

Checks the warehouse and independent reconciliations, retrains the late-delivery models, tests historical-feature timing, and builds the operations brief. Public pinned data downloads are required.

This is CI, not continuous deployment. It does not deploy services or configure branch protection.
Merge gates must be enabled separately in repository settings if desired. The presence of a workflow does not prove a hosted run passed; inspect the Actions run for the commit.

Workflow syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
