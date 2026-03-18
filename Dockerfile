FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Handle dynamic ports for platforms like Render, Railway, etc.
CMD ["sh", "-c", "bokeh serve app --port ${PORT:-5006} --address 0.0.0.0 --allow-websocket-origin=* --use-xheaders"]
