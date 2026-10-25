# Deploy PhantomShield on Vercel with persistent storage

## Why the original deployment fails

The original offline build writes a SQLite file next to `server.py`. Vercel Functions cannot persist writes there. A bundled database can still be readable, so the page/dashboard may load while simulation writes fail. This package uses PostgreSQL when `DATABASE_URL` is set. In Vercel it refuses to fall back to SQLite and explains the missing configuration.

## Required steps

1. Open your existing PhantomShield project in the Vercel dashboard.
2. Under Storage or Marketplace, add/connect **Neon Postgres** to this project. Select a suitable plan and review any provider charges before accepting. A PostgreSQL database from another provider is also supported.
3. In project Settings → Environment Variables, verify that `DATABASE_URL` exists for **Production**, and Preview if you intend to test preview deployments. Use the provider's PostgreSQL connection string with its required SSL settings. The Neon integration may populate it automatically. If a prefix was selected, ensure the variable is named `DATABASE_URL`; the code also accepts `POSTGRES_URL`.
4. Put this package's contents at your repository's deployment root: `vercel.json`, `api/`, `server.py`, `storage.py`, `requirements.txt`, and `web/`. Set Vercel's Root Directory to that folder. Do not deploy only the `web` folder. Use the Other framework preset with no custom build/output overrides; the supplied `vercel.json` defines the Python and static builds.
5. Commit/upload the updated source through your existing deployment workflow, then redeploy. Environment-variable changes require a new deployment. The Python build installs `psycopg[binary]` from `requirements.txt`.
6. Visit `https://YOUR-DOMAIN/api/health`. Expect `{"status":"ok","storage":"postgresql"}`. The first API request initializes a separate `phantomshield` schema with tables and ten fictional decoys automatically.
7. Open the dashboard, launch Multi-Stage Intrusion, and verify events, alerts, timeline, report, and alert status changes. Refresh and check that records persist. Try another browser to confirm that the same hosted database is being read.

Keep the connection string inside Vercel's server-side environment variables. Do not paste it in chat, commit it, or put it in `web/`. `.env.example` is illustrative; the server does not load `.env` files automatically. A provided connection string is used only by Python. The PostgreSQL role must be allowed to create/use the `phantomshield` schema and its tables in its database.

## What this package changes

- Vercel Python Function entry point in `api/index.py`.
- Explicit API and static routing in `vercel.json`.
- Local SQLite preserved without requiring third-party packages.
- Persistent PostgreSQL selected through a server-side connection variable.
- Transaction-scoped locking to serialize correlation and updates across function instances.
- Automatic schema initialization on cold starts.
- Consistent record ordering across both database backends.
- Health endpoint and useful configuration errors; credentials are not exposed in errors/logging.
- Storage indicators reflect PostgreSQL in the hosted dashboard.
- Runtime databases, credentials, archives, and Git metadata excluded from deployment packaging.

Existing local SQLite records are not automatically migrated. The new hosted database starts with its own clean simulation state. This remains a shared single-operator demo: all visitors read the same simulation records and can use Reset Demo. It has no authentication or tenant separation. Keep only one active demo operator/dashboard during presentation.

## Local use remains available

Without `DATABASE_URL` and without `VERCEL=1`, run:

```powershell
python server.py
```

To test PostgreSQL from your own terminal, install the dependencies and set `DATABASE_URL` locally using your provider's private connection string. Never include an actual connection string in screenshots or commits.

```powershell
python -m pip install -r requirements.txt
python server.py
```

## Validation and limits

```powershell
python -m unittest discover -v
node --check web/app.js
node --check web/experience.js
```

The automated tests verify the original detection flows against local SQLite, transaction rollback/persistence, PostgreSQL parameter translation, invalid URL handling, and cloud refusal to use local SQLite. They do not substitute for a real provider-backed PostgreSQL deployment test. No database credentials or Vercel account access were available when preparing this package; its hosted deployment must be verified after you connect the database and redeploy. The original live URL has not been changed by this package.

## Troubleshooting

- `DATABASE_NOT_CONFIGURED`: connect the database, set DATABASE_URL for the current deployment environment, and redeploy.
- `DATABASE_UNAVAILABLE`: inspect Vercel function logs and provider status. Error class/SQLSTATE are logged without the database URL. Check SSL, valid credentials, network access, and schema creation privileges.
- 404 at `/api/health`: ensure the full package and `vercel.json` are deployed from the correct root. A static-only deployment cannot run the backend.
- Health says SQLite: you are viewing a local process or an old deployment; the supplied Vercel build requires PostgreSQL.
- Data differs between deployments: check that Production and Preview intentionally point to the expected database/branches.
- Do not use `/tmp` as a persistent database workaround; separate Vercel instances do not share that file.
