FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

RUN useradd --create-home --uid 10001 candidate \
    && install -d -m 0755 -o candidate -g candidate /workspace \
    && install -d -m 0755 /opt/sb001 \
    && printf 'minimal\n' > /opt/sb001/profile
COPY --chmod=0555 ready.py /opt/sb001/ready
WORKDIR /workspace
USER candidate
CMD ["sleep", "infinity"]
