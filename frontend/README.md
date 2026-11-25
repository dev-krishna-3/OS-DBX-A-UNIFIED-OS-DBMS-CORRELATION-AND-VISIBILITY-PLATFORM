# OS-DBX Frontend

Desktop-first React/Vite interface for the OS-DBX project demo. Account creation and sign-in use the FastAPI backend. Other workspace screens continue to display labeled local illustrative records while their source integrations are completed.

## Run locally

```powershell
cd frontend
npm install
npm run dev
```

Open the local Vite URL printed in the terminal. Use the left navigation to explore the observatory, correlation, incidents, performance, OS/DBMS simulation labs, what-if analysis, and administration.

## API setup

Copy `.env.example` to `.env.local` and set `VITE_API_BASE_URL` to the backend origin (for example, `http://127.0.0.1:8000`). The frontend API gateway lives in `src/api/`; feature services are grouped by authentication, observability, correlation, incidents, and analysis.

The app opens on its authentication page. Signup requires a display name, email, and password; sign-in uses email and password. A Linux UID is managed by the system and is not requested from users. Signup and login responses report whether the backend sent an email notification. Configure SMTP on the backend; never put SMTP credentials in the frontend environment. After signing in, **Administration → Accounts & sign-in** shows the active account and sign-out action.

The `src/features/` directory contains user-facing feature modules. Shared API transport and auth token handling belong in `src/api/client.ts`; feature-specific endpoints belong in their corresponding API module.

## Demo path

Start at **Overview**, select **Run guided demo**, then continue through the process, identity bridge, query, trace, and explanation stages. The unified console also provides local previews for the live streaming observatory, ad-hoc SQL causality, and workload evaluator flows.

All displayed measurements and records are illustrative. Buttons that would poll collectors, execute SQL, create traces, run benchmarks, or persist scenarios explain that backend integration is not connected.
