# kaapi-guardrails
A repo for our experiments with Guardrails so can be integrated with Kaapi

# Kaapi Guardrails

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
![](https://github.com/ProjectTech4DevAI/ai-platform/workflows/Continuous%20Integration/badge.svg)
![GitHub issues](https://img.shields.io/github/issues-raw/ProjectTech4DevAI/kaapi-guardrails)
[![Commits](https://img.shields.io/github/commit-activity/m/ProjectTech4DevAI/kaapi-guardrails)](https://img.shields.io/github/commit-activity/m/ProjectTech4DevAI/kaapi-guardrails)

## Pre-requisites

- [docker](https://docs.docker.com/get-started/get-docker/) Docker
- [uv](https://docs.astral.sh/uv/) for Python package and environment management.

## Project Setup

You can **just fork or clone** this repository and use it as is.

✨ It just works. ✨

### Configure

Create env file using example file

```bash
cp .env.example .env
```

You can then update configs in the `.env` files to customize your configurations.

⚠️ Some services depend on these environment variables being set correctly. Missing or invalid values may cause startup issues.

## Bootstrap & development mode

You have two options to start this dockerized setup:
### Option A: Run migrations & seed data

Use the prestart profile to automatically run database migrations and seed data.
This does **not** reset/drop the database.
```bash
docker compose --profile prestart up prestart
```

### Option B: Start normally

Start the project directly:
```bash
docker compose watch
```
This will start all services in watch mode for development — ideal for local iterations.

Backend is exposed at `http://localhost:8001` (container port `8000` mapped to host `8001`).

### Rebuilding Images

```bash
docker compose up --build -d
```

This is also necessary when:
- Dependencies change in `pyproject.toml` or `uv.lock`
- You modify Dockerfile configurations
- Changes aren't being reflected in the running containers

## Backend Development

Backend docs: [backend/README.md](./backend/README.md).

## Deployment

Deployment docs: [deployment.md](./deployment.md).

## Development

General development docs: [development.md](./development.md).

This includes using Docker Compose, custom local domains, `.env` configurations, etc.

## Release Notes

Release notes file is not currently maintained in this repository.

## Credits

This project was created using [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template). A big thank you to the team for creating and maintaining the template!!!
