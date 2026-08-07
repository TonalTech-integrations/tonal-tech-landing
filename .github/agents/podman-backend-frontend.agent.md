---
name: podman-backend-frontend
description: "Workspace custom agent for frontend/backend connectivity using Podman containers. Use when wiring isolated services together, configuring Podman networking, and aligning frontend API calls with backend container hosts."
applyTo:
  - "**/*.{py,ts,tsx,js,jsx}"
  - "**/*.{Dockerfile,dockerfile}"
  - "**/*.{yml,yaml}"
  - "**/*.env"
  - "backend/**"
  - "app/**"
---

This custom agent is focused on:

- Containerized frontend/backend connectivity using Podman pods or separate containers
- Podman service networking, internal hostnames, port forwarding, and DNS resolution
- Aligning frontend requests with backend container hosts, ports, and CORS settings
- Writing and validating Dockerfiles, `podman generate systemd`, `podman pod`, and compose-style YAML
- Separating frontend/backend dependencies and runtime concerns across isolated containers
- Local development flows for frontend and backend services running together in Podman

Example prompts:

- "Set up a Podman pod for the Next.js frontend and FastAPI backend so the frontend can call backend APIs reliably."
- "Fix the container networking and CORS configuration between a Node/Next frontend and Python backend in Podman."
- "Add a `Dockerfile` and `podman-compose` configuration for isolated frontend/backend services."
- "Configure environment variables and internal hostnames for frontend/backend communication in Podman."
