# Multi-platform index verified on Docker Hub; pin freezes the complete base image.
FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0
WORKDIR /app
COPY .python-version requirements.txt config.json ./
COPY configs/ ./configs/
COPY src/ ./src/
COPY tests/ ./tests/
COPY data/sample/ ./data/sample/
RUN python -m unittest discover -s tests -v
ENTRYPOINT ["python", "src/benchmark.py"]
CMD ["--config", "config.json", "--output", "/results"]
