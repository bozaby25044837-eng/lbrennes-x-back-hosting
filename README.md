# BRENNES X BACK — Real Python Hosting Panel

This is a starter self-hosted VPS panel for your own/trusted Python bots.

## VPS setup (Ubuntu/Debian)
1. Copy this folder to `/opt/brennes-hosting`.
2. Create a non-root user named `hosting` and make the folder owned by it.
3. Create a venv:
   `python3 -m venv .venv`
4. Install:
   `./.venv/bin/pip install -r requirements.txt`
5. Set `ADMIN_PASS` and a strong `SECRET_KEY` in the systemd service.
6. Install the service from `systemd/brennes-hosting.service`.
7. Put nginx config in `/etc/nginx/sites-available/` and enable it.
8. Add HTTPS with your normal TLS setup.

## Important
Uploaded Python code is executed on the server as the service user. Do NOT expose this panel to untrusted users. For a public multi-user hosting service, run each project in an isolated container/VM with CPU, RAM, disk, network and process limits.

The dashboard starts trusted projects with `subprocess.Popen(..., shell=False)`, and captures stdout/stderr into per-project logs.
