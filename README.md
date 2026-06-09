# OpsDeck

**OpsDeck** is a lightweight HomeLab management platform for DevOps users. Manage Linux nodes, Docker services, Kubernetes/K3s workloads, and automation jobs from a clean, modern dashboard.

Built as a portfolio-ready MVP with mock integrations designed for future SSH, Ansible, Docker API, and Kubernetes API connectivity.

![Tech Stack](https://img.shields.io/badge/React-Vite-61DAFB?style=flat-square)
![Tech Stack](https://img.shields.io/badge/FastAPI-Python-009688?style=flat-square)
![Tech Stack](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square)

## Features

- **Dashboard** — Node health summary, service status, recent jobs, last health check
- **Nodes** — CRUD for Linux nodes with resource usage, roles, and environments
- **Node Actions** — Health check, update packages, restart Docker, install Node Exporter, run backup (mock jobs)
- **Services** — Manage Grafana, Prometheus, ArgoCD, Portainer, and more
- **Docker Containers** — View container status, ports, and resource usage (mock data)
- **Kubernetes Workloads** — Track deployments, statefulsets, daemonsets (mock data)
- **Automation Jobs** — Simulated job lifecycle with realistic logs
- **Health Checks** — Node and service health records with status updates
- **Activity Log** — Audit trail of infrastructure events
- **Settings** — SSH key management with encryption, key generation, and connection testing

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Frontend   | React, Vite, TypeScript, Tailwind   |
| Backend    | FastAPI, Python 3.12                |
| Database   | PostgreSQL 16                       |
| ORM        | SQLAlchemy 2.0                      |
| Migrations | Alembic                             |
| API Docs   | FastAPI Swagger/OpenAPI             |

## Quick Start

### Prerequisites

- Docker and Docker Compose

### Run locally

```bash
git clone <your-repo-url>
cd opsdeck
docker compose up --build
```

After startup:

| Service   | URL                              |
|-----------|----------------------------------|
| Frontend  | http://localhost:3000            |
| Backend   | http://localhost:8000            |
| API Docs  | http://localhost:8000/docs       |
| Health    | http://localhost:8000/api/health |

The database is automatically migrated and seeded with demo data on first startup.

### Connect a real node via SSH

1. Open **Settings** → **SSH Credentials**
2. Click **Generate Key Pair** (or paste an existing private key)
3. Copy the **public key** to the target server's `~/.ssh/authorized_keys`
4. Enter the SSH username (e.g. `ubuntu`) and click **Save Credentials**
5. Use **Test SSH** with the server's IP to verify connectivity
6. Add a node with the correct IP and optional per-node SSH user override
7. On the node detail page, click **Run Health Check** for real metrics

## Project Structure

```
opsdeck/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # REST API endpoints
│   │   ├── core/            # Config, database
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   └── mock/            # Mock health checks, jobs, seed data
│   ├── alembic/             # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # API client
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route pages
│   │   ├── layouts/         # App shell
│   │   └── types/           # TypeScript interfaces
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## API Endpoints

### System

| Method | Endpoint          | Description        |
|--------|-------------------|--------------------|
| GET    | `/api/health`     | Liveness check     |
| GET    | `/api/ready`      | Readiness check    |
| GET    | `/api/version`    | App version info   |

### Dashboard

| Method | Endpoint               | Description          |
|--------|------------------------|----------------------|
| GET    | `/api/dashboard/stats` | Dashboard statistics |

### Nodes

| Method | Endpoint                              | Description           |
|--------|---------------------------------------|-----------------------|
| GET    | `/api/nodes`                          | List all nodes        |
| POST   | `/api/nodes`                          | Create node           |
| GET    | `/api/nodes/{node_id}`                | Get node details      |
| PUT    | `/api/nodes/{node_id}`                | Update node           |
| DELETE | `/api/nodes/{node_id}`                | Delete node           |
| POST   | `/api/nodes/{node_id}/health-check`   | Run health check      |
| POST   | `/api/nodes/{node_id}/actions/{action}` | Run automation action |

### Services

| Method | Endpoint                                   | Description      |
|--------|--------------------------------------------|------------------|
| GET    | `/api/services`                            | List services    |
| POST   | `/api/services`                            | Create service   |
| GET    | `/api/services/{service_id}`               | Get service      |
| PUT    | `/api/services/{service_id}`               | Update service   |
| DELETE | `/api/services/{service_id}`               | Delete service   |
| POST   | `/api/services/{service_id}/health-check`  | Run health check |

### Containers

| Method | Endpoint                        | Description        |
|--------|---------------------------------|--------------------|
| GET    | `/api/containers`               | List containers    |
| POST   | `/api/containers`               | Create container   |
| GET    | `/api/containers/{container_id}`| Get container      |
| PUT    | `/api/containers/{container_id}`| Update container   |
| DELETE | `/api/containers/{container_id}`| Delete container   |

### Kubernetes Workloads

| Method | Endpoint                        | Description        |
|--------|---------------------------------|--------------------|
| GET    | `/api/workloads`                | List workloads     |
| POST   | `/api/workloads`                | Create workload    |
| GET    | `/api/workloads/{workload_id}`  | Get workload       |
| PUT    | `/api/workloads/{workload_id}`  | Update workload    |
| DELETE | `/api/workloads/{workload_id}`  | Delete workload    |

### Jobs

| Method | Endpoint                    | Description    |
|--------|-----------------------------|----------------|
| GET    | `/api/jobs`                 | List jobs      |
| GET    | `/api/jobs/{job_id}`        | Get job        |
| POST   | `/api/jobs/{job_id}/rerun`  | Rerun job      |

### Settings (SSH)

| Method | Endpoint                    | Description                    |
|--------|-----------------------------|--------------------------------|
| GET    | `/api/settings/ssh`         | Get SSH config status          |
| PUT    | `/api/settings/ssh`         | Save SSH credentials           |
| DELETE | `/api/settings/ssh`         | Remove SSH credentials         |
| POST   | `/api/settings/ssh/test`    | Test SSH connection            |
| POST   | `/api/settings/ssh/generate`| Generate new SSH key pair        |

### Health Checks & Activity

| Method | Endpoint              | Description           |
|--------|-----------------------|-----------------------|
| GET    | `/api/health-checks`  | List health checks    |
| GET    | `/api/activity-logs`  | List activity logs    |

### Node SSH

| Method | Endpoint                              | Description              |
|--------|---------------------------------------|--------------------------|
| POST   | `/api/nodes/{node_id}/test-connection`| Test SSH to a node       |
| POST   | `/api/nodes/{node_id}/sync-containers`| Sync Docker containers via SSH |

## Database Migrations

Migrations run automatically on container startup. For manual use:

```bash
# Inside backend container or local venv
cd backend
alembic upgrade head        # Apply migrations
alembic revision --autogenerate -m "description"  # Create new migration
alembic downgrade -1        # Rollback one revision
```

### Seed demo data

```bash
python -c "
from app.core.database import SessionLocal
from app.mock.seed_data import seed_database
seed_database(SessionLocal())
"
```

## Demo Data

The seed script populates:

| Entity            | Count |
|-------------------|-------|
| Nodes             | 3     |
| Services          | 8     |
| Containers        | 10    |
| K8s Workloads     | 6     |
| Automation Jobs   | 8     |
| Health Checks     | 15    |
| Activity Logs     | 20    |

**Demo nodes:** `raspberry-pi-01`, `ubuntu-vm-01`, `k3s-master-01`

**Demo services:** Grafana, Prometheus, ArgoCD, Portainer, Nginx Proxy Manager, MinIO, PostgreSQL, Redis

## Architecture Notes

The backend is structured for future real integrations:

```
app/
├── mock/                    # Current: mock implementations
│   ├── health_check_mock.py # → Future: services/ssh_health.py
│   └── job_mock.py          # → Future: services/ansible_runner.py
└── services/                # Business logic layer (extensible)
```

Mock integrations today; swap module implementations later without changing API contracts.

## Future DevOps Roadmap

### Application Integrations (in-app)

- [x] SSH key management from Settings UI (encrypted at rest)
- [x] Real SSH health checks and metrics via Paramiko
- [x] Real SSH automation jobs (when credentials configured)
- [x] Docker container sync via SSH (`docker ps` / `docker stats`)
- [ ] Ansible Runner for node automation
- [ ] Docker API client for live container sync
- [ ] Kubernetes client for K3s workload sync
- [ ] Prometheus metrics scraping
- [ ] Grafana dashboard deep-links
- [ ] OAuth2 / API key authentication

### Planned DevOps Infrastructure

> **Not implemented in this repo** — reserved for a separate infrastructure layer.

- **Docker image build** — Multi-stage builds for backend and frontend, published to a container registry
- **GitHub Actions CI/CD** — Lint, test, build, and push images on every PR and release
- **ECR image registry** — AWS Elastic Container Registry for production images
- **Helm chart** — Kubernetes packaging for OpsDeck deployment
- **ArgoCD GitOps deployment** — Declarative sync from Git to cluster
- **K3s local deployment branch** — Lightweight on-prem cluster for HomeLab
- **AWS cloud deployment branch** — Production-grade cloud deployment path
- **EKS** — Managed Kubernetes for cloud workloads
- **RDS** — Managed PostgreSQL for production database
- **Route53** — DNS for public endpoints
- **ACM** — TLS certificates for HTTPS
- **Prometheus and Grafana** — Cluster and application observability stack

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://opsdeck:opsdeck@localhost:5432/opsdeck
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## License

MIT
