# One-shot provisioner: stdlib + numpy only. Build context is the repository root.
FROM python:3.11-slim
RUN pip install --no-cache-dir numpy
WORKDIR /work
COPY src/tts_bench /opt/src/tts_bench
ENV PYTHONPATH=/opt/src PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "tts_bench.evaluation"]
