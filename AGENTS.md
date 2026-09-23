# AGENTS: Dhara Pulse — quick workspace guide for AI coding agents

Purpose: Help automated coding agents (Copilot, CI bots) understand this repository quickly and act safely.

Quick facts
- **Frontend**: Vite + React. See [frontend/README.md](frontend/README.md) for template notes.
- **Backend**: FastAPI app. See [backend/main.py](backend/main.py#L1-L45) (single-file API).

Run & build
- Frontend dev: `npm run dev` (from `frontend/`) — uses Vite.
- Frontend build: `npm run build`.
- Backend dev: `uvicorn main:app --reload` (run from `backend/`).

Conventions & pointers for agents
- Work in the folder corresponding to the task: frontend changes go under `frontend/`, backend under `backend/`.
- Frontend scripts are in [frontend/package.json](frontend/package.json). Use `npm install` in that folder first.
- The backend is a minimal FastAPI service with CORS enabled; avoid changing global CORS policy without confirming the intent in an issue/PR.
- There are no tests or CI configurations in the repo — add tests or CI only after a discussion/issue.

Common pitfalls
- No `requirements.txt` or pyproject found for backend — ensure the reviewer knows which Python deps to install (FastAPI, uvicorn, requests).
- Frontend depends on `leaflet` (map library) — verify CSS and asset loading when adding maps.

When editing
- Keep commits small and focused per folder. Run `npm run lint` in `frontend/` when changing UI code.
- If adding new APIs, update `backend/main.py` and include API docstrings and example responses.

Suggested next customizations
- Create a small `.github/copilot-instructions.md` or expand this file with contribution guidelines and a short development checklist.
- Add `AGENTS/frontend-skill.md` to document UI patterns and component conventions if the frontend grows.

If anything here is unclear, ask for the preferred dependency lists or the intended CI workflow before making large changes.
