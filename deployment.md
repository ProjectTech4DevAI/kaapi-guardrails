# FastAPI Project - Deployment

## Preparation

1. Create production env values from `.env.example`.
2. Set `ENVIRONMENT=production`.
3. Set `POSTGRES_*` for your production database.
4. Set `AUTH_TOKEN` as a SHA-256 hex digest (64 lowercase chars) of your bearer token.
5. Set `ALLOWED_IPS` to kaapi-backend's source IP(s), comma-separated. Required in production — the
   service will not start without it.
6. Optionally set `GUARDRAILS_HUB_API_KEY` and `SENTRY_DSN`.

Generate AUTH token hash:

```bash
echo -n "your-plain-text-token" | shasum -a 256
```

## Caller access

Only kaapi-backend may call this service. Requests must carry `Authorization: Bearer <token>` plus
`X-ORGANIZATION-ID` / `X-PROJECT-ID`, and must originate from an IP in `ALLOWED_IPS`.

Confirm `ALLOWED_IPS` matches the IP guardrails actually sees. If NAT or a different network
interface is in play, the observed source will differ from what you expect and every request will be
rejected with `403`. Only the health check is exempt.

Note: the check reads the real connection source and ignores `X-Forwarded-For`. If a reverse proxy
or load balancer is ever placed in front of this service, all traffic will appear to come from the
proxy and this must be revisited.

## Deploy the FastAPI Project

Build and start backend:

```bash
docker compose build backend
docker compose up -d backend
```

Run migrations and initial setup (recommended before or during first rollout):

```bash
docker compose --profile prestart up prestart
```

Default host endpoint:
- API/Docs host: `http://<host>:8001`
- Health check: `http://<host>:8001/api/v1/utils/health-check/`

## Continuous Deployment (CD)

CI workflow is defined in `.github/workflows/continuous_integration.yml`.
It runs dependency install, Guardrails validator installation, migrations, pre-commit checks, and tests.
