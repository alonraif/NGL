# NGL Production Deployment on Linux

This guide walks through deploying NGL on a fresh Linux host (Ubuntu/Debian family) using Docker Compose with HTTPS support.

## 1. Prerequisites

- 64-bit Linux host (tested on Ubuntu 22.04 LTS)
- Public DNS record pointing to the server (required for Let’s Encrypt)
- Open firewall ports: `22` (SSH), `80` (HTTP), `443` (HTTPS)
- sudo/root access

## 2. Install System Packages

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release git
```

Add Docker’s repository and install the engine + Compose plugin:

```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

## 3. Clone the Repository

```bash
sudo mkdir -p /opt/ngl
sudo chown $USER:$USER /opt/ngl
cd /opt/ngl
git clone https://github.com/alonraif/NGL.git .
```

Optionally check out a tagged release:

```bash
git checkout v3.0.0   # adjust to the desired tag
```

## 4. Configure Environment

Copy the sample environment file and edit it:

```bash
cp .env.example .env
nano .env
```

Update at minimum:
- `POSTGRES_PASSWORD` – strong database password
- `JWT_SECRET_KEY` – generate with `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`
- `CORS_ORIGINS` – include your production domain
- `REACT_APP_API_URL` – e.g. `https://your-domain.com/api`

## 5. Launch the Stack

```bash
docker compose up -d --build
```

Verify containers:

```bash
docker compose ps
```

## 6. Initialize Database & Admin User

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python3 init_admin.py
```

Record the default admin credentials (`admin` / `Admin123!`). You will be prompted to change the password after the first login.

## 7. Configure Firewall (optional)

Using `ufw`:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 8. Access the Application

Visit `http://your-domain` to verify the login screen. Sign in with the admin credentials, then update the password via **Profile → Change Password**.

## 9. HTTPS Setup

Open **Admin → SSL** and choose one of the options:

### Let’s Encrypt
1. Confirm DNS A/AAAA records resolve to the server.
2. Enter the primary domain and any SAN entries.
3. Click **Request Certificate**. The ACME challenge is served from `/var/www/certbot` and certificates are stored under `/etc/letsencrypt` (mounted into the backend, Celery, and frontend containers).
4. Once status is `verified`, enable **Enforce HTTPS**. This writes redirect/HSTS snippets to `/etc/nginx/runtime`.

### Uploaded Certificate
1. Select **Uploaded** mode.
2. Paste the PEM-encoded private key, certificate, and optional chain.
3. Save and enable enforcement once the certificate metadata appears.

Celery Beat runs daily renewal checks for Let’s Encrypt certificates and surface warnings when uploaded certificates near expiry.

## 10. Health Checks

- Application health: `curl -I https://your-domain/api/health`
- SSL health (from Admin → SSL): click **Run Health Check** or trigger via API (`POST /api/admin/ssl/health-check`).
- Container logs:
  ```bash
  docker compose logs -f backend
  docker compose logs -f frontend
  docker compose logs -f celery_worker
  ```

## 11. Upgrades

```bash
cd /opt/ngl
git pull
docker compose pull
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

## 12. Backups

- **Database** (`postgres_data` volume):
  ```bash
  docker compose exec postgres pg_dump -U ngl_user ngl_db > ngl_backup.sql
  ```
- **Uploads** (`uploads` volume) if you retain original log archives.
- **Certificates** (`certbot_certs` volume) if you use uploaded material.

Use `docker run --rm -v volume_name:/data -v $(pwd):/backup busybox tar cvzf /backup/volume_name.tgz /data` to archive named volumes.

## 13. Troubleshooting

- Ensure ports 80/443 are free (no other web server running).
- Check Celery Beat logs if SSL renewals are not firing: `docker compose logs celery_beat`.
- If Let’s Encrypt issuance fails, review `/var/log/nginx/error.log` and ensure DNS is correct.
- To restart services:
  ```bash
  docker compose restart
  ```

The application is now production-ready on Linux with automated HTTPS support.
