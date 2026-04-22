FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    fio \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY resources/requirements.txt ./resources/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r resources/requirements.txt

COPY . .

RUN if [ -f mypylib/requirements.txt ]; then pip install --no-cache-dir -r mypylib/requirements.txt; fi && \
    if [ -f mypyconsole/requirements.txt ]; then pip install --no-cache-dir -r mypyconsole/requirements.txt; fi

RUN mkdir -p db config bin

CMD ["python3", "mytonprovider.py"]