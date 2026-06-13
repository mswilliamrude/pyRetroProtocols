FROM python:3.9-slim-bullseye

# Because Linux is superior, we'll install some standard Linux utilities
RUN apt-get update && apt-get install -y \
    procps \
    lsof \
    net-tools \
    socat \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire pyzmodem codebase into the container
COPY . /app

# Install our testing dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio

# Drop straight into a bash shell so you can do Linux things
CMD ["/bin/bash"]
