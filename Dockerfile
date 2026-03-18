FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the default Bokeh port
EXPOSE 5006

CMD ["bokeh", "serve", "--port", "5006", "--address", "0.0.0.0", "--allow-websocket-origin=*", "app/main.py"]
