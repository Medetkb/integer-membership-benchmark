# Pinned environment

The benchmark and tests use only the CPython standard library. The complete set of third-party Python requirements is empty. `.python-version` pins **3.12.14**; `requirements.txt` explains why there are no package lines. No loosely pinned package dependencies are hidden in the project.

The optional Dockerfile starts from:

```text
python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
```

This is the multi-platform index digest reported on the [official Python image detail page](https://hub.docker.com/layers/library/python/3.12.14-slim-bookworm/images/sha256-1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a), checked on 8 October 2026. The displayed amd64 manifest is `sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a`. The Dockerfile uses the index, allowing Docker to select the native architecture from that frozen image set.

There is no `apt install`, `pip install` or other dependency resolution in this Dockerfile. The existing image content is fixed by its digest. The build copies the source and sample, then runs the same standard-library unit tests as the native path. A future dependency or image update must be deliberate and must be recorded before collecting a new study.

**Validation boundary:** native CPython 3.12.14 execution was tested on macOS arm64. Docker was not installed in the preparation environment. The digest and Dockerfile are supplied, but a successful Docker build is not claimed. Run the README Docker commands if using that environment for submission.

The image does not fix the host CPU, host kernel, cooling, power mode or other running programs. Record the CPU model, installed RAM and power mode in your Week 7 run notes, keep one machine throughout the study, and retain `environment.json` and `config.snapshot.json`. Never combine native and container measurements into a single confirmatory analysis.
