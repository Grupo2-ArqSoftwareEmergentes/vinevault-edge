# Vinevault Edge + Kafka Deploy Guide in AWS Lightsail

This document summarizes the deploy flow we used in Lightsail for the edge service and Kafka, plus the most common issues we hit and how to resolve them quickly.

## Goal

- Run the edge service in a Lightsail Ubuntu VM.
- Run Kafka in Docker on the same VM.
- Allow the edge to talk to Kafka locally.
- Allow the core backend, running outside the VM, to connect to Kafka through the public IP.
- Keep the setup recoverable after a VM reboot.

## Architecture used in this setup

- Edge service:
  - Runs directly on the VM with `uv run python app.py`
  - Listens on port `5000`
  - Uses the local Kafka bootstrap server `localhost:9092`
- Kafka:
  - Runs in Docker on the same VM
  - Internal listener for the edge: `localhost:9092`
  - External listener for the core backend: `54.166.106.10:9094` in our session

## Important values from the session

- VM public IP: `54.166.106.10`
- VM private IP: `172.26.8.124`
- Edge HTTP URL from outside the VM: `http://54.166.106.10:5000`
- Kafka bootstrap for the edge: `localhost:9092`
- Kafka bootstrap for the core backend: `54.166.106.10:9094`
- Core API URL: `https://vinevault-core-1-1-0.onrender.com`
- Core API key used in the session: `edge-test-key-001`

## 1. Lightsail networking

Open these inbound firewall rules in Lightsail:

- `22/TCP` for SSH
- `5000/TCP` for the edge HTTP API
- `9094/TCP` for external Kafka access from the core backend

Optional:

- `80/TCP` only if you put a reverse proxy in front of the edge

Notes:

- The edge app runs on port `5000`, not `80`.
- Kafka should not expose `9092` to the internet in this setup.
- Keep `9092` internal for the edge VM only.

## 2. Prepare the VM

### Check the base system

```bash
cat /etc/os-release
uname -m
whoami
```

Expected in our session:

- Ubuntu 22.04
- `x86_64`
- user `ubuntu`

### Install Docker

If Docker is not installed:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker
```

Verify:

```bash
docker --version
docker-compose --version
sudo docker ps
```

### Install uv

If `uv` is missing:

```bash
sudo snap install astral-uv --classic
uv --version
```

### Clone the repo

```bash
cd ~
git clone https://github.com/Grupo2-ArqSoftwareEmergentes/vinevault-edge.git
cd vinevault-edge
```

## 3. Environment file

The repo ships with `.env.example`, not `.env`.

Create the real file:

```bash
cp .env.example .env
```

Recommended values for this deploy:

```env
EDGE_DATABASE_PATH=vinevault_edge.db
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
EDGE_PUBLIC_BASE_URL=http://54.166.106.10:5000
CORE_BASE_URL=https://vinevault-core-1-1-0.onrender.com
EDGE_CORE_API_KEY=edge-test-key-001
EDGE_CORE_DEVICES_PAGE_SIZE=50
EDGE_CORE_DEVICES_SYNC_GRACE_SECONDS=15
EDGE_CORE_DEVICES_SYNC_RETRY_SECONDS=30
EDGE_CORS_ALLOWED_ORIGINS=*
EDGE_CORS_ALLOWED_HEADERS=Content-Type,X-Hardware-Id,X-API-Key
```

### Why these values

- `KAFKA_BOOTSTRAP_SERVERS=localhost:9092`
  - The edge and Kafka run on the same VM.
- `EDGE_PUBLIC_BASE_URL=http://54.166.106.10:5000`
  - This is the public URL from outside the VM.
- `CORE_BASE_URL=https://vinevault-core-1-1-0.onrender.com`
  - The core backend is external.
- `EDGE_CORE_API_KEY`
  - Needed for the HTTP fallback sync to the core.

## 4. Kafka Docker compose

We adjusted Kafka to support two listeners:

- internal listener for the edge
- external listener for the core backend

The active compose files in the repo were updated to advertise:

- `PLAINTEXT://localhost:9092`
- `EXTERNAL://54.166.106.10:9094`

This means:

- the edge uses `localhost:9092`
- the core backend uses `54.166.106.10:9094`

## 5. Start sequence after a fresh boot

If you have not automated startup yet, the manual flow is:

```bash
sudo systemctl start docker
sudo docker start kafka
cd ~/vinevault-edge
uv run python app.py
```

Important:

- `sudo docker start kafka` is safer than `docker-compose up -d` if the container already exists.
- `uv run python app.py` keeps the terminal busy while the edge runs.

## 6. Starting Kafka the first time

If the Kafka container does not exist yet:

```bash
cd ~/vinevault-edge
sudo docker-compose -f docker-compose-kafka.yml up -d
sudo docker ps
```

If the container already exists after a reboot:

```bash
sudo docker start kafka
```

## 7. Verify the deployment

### Check Kafka container

```bash
sudo docker ps
```

Expected:

- `apache/kafka:latest`
- container name `kafka`
- ports `9092` and `9094` mapped

### Check the edge app

Run:

```bash
uv run python app.py
```

Expected logs:

- `Running on http://127.0.0.1:5000`
- `Running on http://172.26.8.124:5000`

The private IP is normal inside the VM. Outside the VM, use the public IP.

### Check Kafka topics

Inside the Kafka container:

```bash
sudo docker exec -it kafka bash
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

In our session, the topics already appeared, which confirmed Kafka was healthy and the edge had bootstrapped its topics.

### Check consumer groups

Inside the Kafka container:

```bash
/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list
```

The group `vinevault-core` appeared with the consumer host IP `74.220.48.30`, which confirmed the core backend was connecting from outside the VM.

To inspect a group in detail:

```bash
/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group vinevault-core
```

## 8. What each result meant in the session

### Topics listed with `kafka-topics.sh`

If you see topics such as:

- `vinevault.device.alert.incident.changed`
- `vinevault.device.commands.acknowledged`
- `vinevault.device.commands.pending`
- `vinevault.device.presence.changed`
- `vinevault.device.telemetry.recorded`
- `vinevault.provisioning.devices.changed`
- `vinevault.provisioning.devices.sync.requested`

This means:

- Kafka is alive
- the topics exist
- the edge likely bootstrapped them at startup

It does **not** by itself prove that the core backend connected.

### Consumer group `vinevault-core`

When we ran:

```bash
/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group vinevault-core
```

We saw:

- `CONSUMER-ID`
- `HOST` with an external IP
- offsets and lag values

That confirmed the core backend was connected and consuming from Kafka.

## 9. Common problems and quick fixes

### Problem: `docker` command not found

Fix:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
```

### Problem: `docker-compose` or Docker socket permission denied

Symptom:

- `PermissionError: [Errno 13] Permission denied`

Fix:

```bash
sudo docker-compose -f docker-compose-kafka.yml up -d
```

Optional permanent fix:

```bash
sudo usermod -aG docker ubuntu
newgrp docker
```

### Problem: `uv` not found

Fix:

```bash
sudo snap install astral-uv --classic
```

### Problem: `sqlite3` not found

Fix:

```bash
sudo apt update
sudo apt install -y sqlite3
```

### Problem: `.env` not found

Fix:

```bash
cp .env.example .env
```

### Problem: Kafka topics not visible

Possible causes:

- Kafka container is not running
- wrong bootstrap server
- ports not open in Lightsail

Quick checks:

```bash
sudo docker ps
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Problem: Core backend cannot connect to Kafka

Check all of these:

- Lightsail firewall has `9094/TCP` open
- Kafka advertises `EXTERNAL://54.166.106.10:9094`
- the core backend uses:

```env
KAFKA_BOOTSTRAP_SERVERS=54.166.106.10:9094
```

### Problem: Edge is reachable only inside the VM

Symptom:

- `http://172.26.8.124:5000` works only from inside the VM

Fix:

- Use the public IP externally:

```text
http://54.166.106.10:5000
```

- Make sure port `5000` is open in Lightsail

## 10. Reboot checklist

If the VM is restarted and nothing is automated yet:

1. Start Docker

```bash
sudo systemctl start docker
```

2. Start Kafka if the container already exists

```bash
sudo docker start kafka
```

3. Start the edge

```bash
cd ~/vinevault-edge
uv run python app.py
```

## 11. Recommended automation

To avoid manual startup after every reboot:

- Add `restart: unless-stopped` to the Kafka container
- Create a `systemd` service for the edge

This gives you:

- Docker starts on boot
- Kafka restarts automatically
- the edge starts automatically

## 12. Notes for someone new to the project

- Do not confuse:
  - private VM IP: `172.26.8.124`
  - public VM IP: `54.166.106.10`
- For local communication inside the VM:
  - Kafka: `localhost:9092`
  - Edge HTTP: `localhost:5000`
- For external clients:
  - Edge HTTP: `http://54.166.106.10:5000`
  - Kafka external listener: `54.166.106.10:9094`

## 13. Fast troubleshooting flow

If something fails, check in this order:

1. VM firewall rules in Lightsail
2. Docker service status
3. Kafka container status
4. Edge process status
5. `.env` values
6. Kafka topics and consumer groups

This usually resolves most startup issues in minutes.
