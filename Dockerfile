FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip wheel --wheel-dir /wheels ".[all-formats]"


FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93 AS runtime

LABEL org.opencontainers.image.title="Omnixform" \
    org.opencontainers.image.description="A local-first file conversion CLI" \
    org.opencontainers.image.version="0.1.0" \
    org.opencontainers.image.source="https://github.com/ionnixf/omnixform" \
    org.opencontainers.image.licenses="MIT"

ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/home/omnixform \
    PATH=/opt/omnixform/bin:$PATH \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libreoffice pandoc \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 omnixform \
    && python -m venv /opt/omnixform

COPY --from=builder /wheels /wheels
RUN /opt/omnixform/bin/pip install --no-index /wheels/*.whl \
    && rm -rf /wheels

WORKDIR /work
RUN chown omnixform:omnixform /work
USER omnixform

ENTRYPOINT ["omnix"]
CMD ["--help"]
