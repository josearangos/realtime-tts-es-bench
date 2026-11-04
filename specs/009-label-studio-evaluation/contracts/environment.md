# Contract: Environment Configuration (`evaluation/.env`)

| Variable | Default (in `.env.example`) | Purpose |
|---|---|---|
| `LS_VERSION` | `1.23.2` (latest stable) | Label Studio image tag |
| `LS_BIND` | `127.0.0.1` | host interface; anything else is explicit exposure |
| `LS_PORT` | `8080` | host port |
| `LS_ADMIN_USER` | `admin@eval.invalid` | admin account |
| `LS_ADMIN_PASSWORD` | `change-me` | refused when `LS_BIND` is not loopback |
| `LS_API_TOKEN` | `change-me-token` | token used by provisioner/export |
| `LS_ADMIN_*` / `LS_API_TOKEN` | local only | created on the host; not external API keys, no vendor account needed |
| `EVAL_PROVISION` | `1` | `0` disables auto-provisioning |

Compose facts (asserted by a config test): published port bound to `${LS_BIND}`; named volume `ls-data`; healthcheck on the LS health endpoint; `provisioner` `depends_on` healthy; audio dir mounted read-only at the LS local-files root; private mapping not mounted in `label-studio`; sign-up disabled; no secrets in committed files; `.env` git-ignored.
