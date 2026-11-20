# OrderFlow authoring and validation

This source package contains the candidate starter, three stage briefs, an evaluator-only rubric, and known Stage A and B reference implementations. The manifest is a draft until the runtime image and artifact digests are published. Serve each stage's instructions when its stage becomes active. The candidate bundle contains the independent brief. The assisted and defense briefs are supplied separately by the orchestration service.

## Validate the authored package

Use Python 3.12, a non-root user, and the server binaries for PostgreSQL 16. The verification command creates its own throwaway cluster in a private temporary directory, starts PostgreSQL on a Unix socket, and shuts it down on exit. It accepts only the starter and references bundled here. Run real candidate submissions through the managed execution and isolated grading planes.

```sh
python -m venv /tmp/orderflow-author
/tmp/orderflow-author/bin/pip install -r assessments/001-orderflow/candidate/requirements.txt
/tmp/orderflow-author/bin/python -m unittest discover -s assessments/001-orderflow/tests -p test_package.py
/tmp/orderflow-author/bin/python assessments/001-orderflow/tests/verify.py --postgres-bin /usr/lib/postgresql/16/bin
```

Each variant receives an independent database and a non-superuser application role. The authoring harness applies migrations twice, runs the candidate's visible suite, launches the API as a separate process, and runs external black-box probes. The stock race holds a row lock until PostgreSQL confirms two blocked request connections. A forced inventory-write failure checks for partial commits. The starter must exhibit both exact failure signatures. Stage A must pass the independent invariants. Stage B must pass both stages' checks and recover a committed response following an actual API process restart.

The evaluator guide includes the reference approaches, review anchors, defense evidence, calibration examples and limitations. Pilot calibration still requires qualified human participants and reviewers.

## Build the candidate artifact

```sh
python assessments/001-orderflow/tests/package.py /tmp/orderflow-candidate.tar
```

The packaging command prints the SHA-256 digest of a reproducible tar built from explicitly listed ordinary files. Stage B requirements, reference code, evaluator tests, and private rubrics sit outside its input. The candidate and evaluator directories must be distributed separately.

For release, supply the registry digest of the approved runtime image with `python assessments/001-orderflow/tests/package.py OUTPUT_DIRECTORY --image-digest sha256:…`. The command creates a new directory containing distinct candidate and evaluator tars, stage briefs, and a manifest recording the digest of every artifact and brief.
