FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
RUN pip install --no-cache-dir --user slither-analyzer solc-select && \
    solc-select install 0.8.20 0.8.24 0.8.26 0.8.28 0.6.12 0.7.6 0.5.16 0.4.24 && solc-select use 0.8.24
WORKDIR /home/user/app
COPY --chown=user server/package.json server/package-lock.json ./
RUN npm ci --omit=dev
COPY --chown=user server/server.mjs server/scanner.py server/sample-report.json ./
ENV PORT=7860 PY=python3
EXPOSE 7860
CMD ["node", "server.mjs"]
