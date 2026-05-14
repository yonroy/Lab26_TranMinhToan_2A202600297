FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV DB_PATH=/data/students.db \
    MCP_TRANSPORT=http \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

CMD ["python", "mcp_server.py"]
