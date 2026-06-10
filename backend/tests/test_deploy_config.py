from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_api_artifact_mount_is_writable_for_run_state() -> None:
    compose = (REPO_ROOT / "deploy" / "docker-compose.api.yml").read_text()

    assert "../local-artifacts:/app/local-artifacts:rw" in compose
    assert "../local-artifacts:/app/local-artifacts:ro" not in compose
    assert "container_name: sidira-api" in compose


def test_ec2_deploy_prepares_artifact_tree_for_container_user() -> None:
    deploy = (REPO_ROOT / "deploy" / "ec2-api-deploy.sh").read_text()
    readme = (REPO_ROOT / "deploy" / "README.md").read_text()

    assert 'CONTAINER_UID="${SIDIRA_CONTAINER_UID:-10001}"' in deploy
    assert 'CONTAINER_GID="${SIDIRA_CONTAINER_GID:-10001}"' in deploy
    assert 'chown -R "${CONTAINER_UID}:${CONTAINER_GID}" "$REPO_DIR/local-artifacts"' in deploy
    assert '-v "$REPO_DIR/local-artifacts:/app/local-artifacts:rw"' in deploy
    assert "sudo chown -R 10001:10001 local-artifacts" in readme


def test_ec2_deploy_exports_database_runtime_settings() -> None:
    deploy = (REPO_ROOT / "deploy" / "ec2-api-deploy.sh").read_text()

    assert 'database_url="$(ssm_value DATABASE_URL)"' in deploy
    assert 'auto_migrate="$(ssm_value SIDIRA_AUTO_MIGRATE)"' in deploy
    assert 'write_env DATABASE_URL "$database_url"' in deploy
    assert 'write_env SIDIRA_AUTO_MIGRATE "$auto_migrate"' in deploy


def test_ec2_deploy_writes_compose_safe_env_file() -> None:
    deploy = (REPO_ROOT / "deploy" / "ec2-api-deploy.sh").read_text()

    assert 'COMPOSE_ENV_FILE="${SIDIRA_COMPOSE_ENV_FILE:-${ENV_FILE}.compose}"' in deploy
    assert 'compose_value="${raw_value//\\$/\\$\\$}"' in deploy
    assert 'printf \'%s=%s\\n\' "$key" "$raw_value" >> "$ENV_FILE"' in deploy
    assert 'printf \'%s=%s\\n\' "$key" "$compose_value" >> "$COMPOSE_ENV_FILE"' in deploy
    assert 'SIDIRA_API_ENV_FILE="$COMPOSE_ENV_FILE" \\' in deploy
    assert '--env-file "$ENV_FILE"' in deploy


def test_ec2_deploy_generates_backend_compatible_local_credential_key() -> None:
    deploy = (REPO_ROOT / "deploy" / "ec2-api-deploy.sh").read_text()

    assert "openssl rand -hex 32" not in deploy
    assert "openssl rand -base64 32 | tr '+/' '-_'" in deploy


def test_ec2_deploy_fails_on_ssm_access_errors() -> None:
    deploy = (REPO_ROOT / "deploy" / "ec2-api-deploy.sh").read_text()

    assert "2>/dev/null || true" not in deploy
    assert "ParameterNotFound" in deploy
    assert 'echo "failed to read ${PARAM_PREFIX}/${name}: ${output}" >&2' in deploy


def test_ec2_deploy_builds_before_replacing_live_containers() -> None:
    deploy = (REPO_ROOT / "deploy" / "ec2-api-deploy.sh").read_text()

    assert deploy.index(
        "docker compose -p sidira -f deploy/docker-compose.api.yml build"
    ) < deploy.index("docker compose -p sidira -f deploy/docker-compose.api.yml up -d")
    assert deploy.index("docker build -t sidira-api:latest backend") < deploy.index(
        "docker rm -f sidira-api sidira-caddy"
    )


def test_public_api_is_gated_by_backend_internal_key() -> None:
    caddy = (REPO_ROOT / "deploy" / "Caddyfile.api").read_text()
    compose = (REPO_ROOT / "deploy" / "docker-compose.api.yml").read_text()
    deploy = (REPO_ROOT / "deploy" / "ec2-api-deploy.sh").read_text()
    app = (REPO_ROOT / "backend" / "sidira_simulator" / "main.py").read_text()

    assert "reverse_proxy api:8000" in caddy
    assert "@web_proxy path /_sidira_web_proxy/*" in caddy
    assert "basic_auth" in caddy
    assert "header_up -Authorization" in caddy
    assert "header_up X-Sidira-Internal-Key {$SIDIRA_INTERNAL_API_KEY}" in caddy
    # Two web-proxy branches since #149: the Clerk branch (matched first) promotes
    # the carrier token into Authorization and drops the carrier; the tokenless
    # branch strips Authorization. Both hop-auth before attaching the internal key.
    clerk_start = caddy.index("handle @web_proxy_clerk {")
    tokenless_start = caddy.index("handle @web_proxy {")
    assert clerk_start < tokenless_start
    clerk_branch = caddy[clerk_start:tokenless_start]
    tokenless_branch = caddy[tokenless_start:]
    for branch in (clerk_branch, tokenless_branch):
        assert branch.index("basic_auth") < branch.index(
            "header_up X-Sidira-Internal-Key {$SIDIRA_INTERNAL_API_KEY}"
        )
    assert (
        "header_up Authorization {http.request.header.X-Sidira-Clerk-Authorization}" in clerk_branch
    )
    assert "header_up -X-Sidira-Clerk-Authorization" in clerk_branch
    assert (
        tokenless_branch.index("basic_auth")
        < tokenless_branch.index("header_up -Authorization")
        < tokenless_branch.index("header_up X-Sidira-Internal-Key {$SIDIRA_INTERNAL_API_KEY}")
    )
    assert "header_up -Authorization" not in clerk_branch.replace(
        "header_up -X-Sidira-Clerk-Authorization", ""
    )
    assert 'request.headers.get("x-sidira-internal-key")' in app
    # /health (and the signature-verified Clerk webhook) bypass the gates via the
    # _PUBLIC_PATHS allowlist.
    assert "request.url.path in _PUBLIC_PATHS" in app
    assert '"/health"' in app
    assert 'JSONResponse({"detail": "Not found"}, status_code=404)' in app
    assert "SIDIRA_API_ENV_FILE" in compose
    assert "SIDIRA_INTERNAL_API_KEY" in deploy
    assert "SIDIRA_WEB_PROXY_BASIC_AUTH_USER" in deploy
    assert "SIDIRA_WEB_PROXY_BASIC_AUTH_HASH" in deploy
    assert '--env-file "$ENV_FILE"' in deploy


def test_frontend_uses_same_origin_proxy_without_internal_api_key() -> None:
    api_client = (REPO_ROOT / "frontend" / "lib" / "api.ts").read_text()
    route = (REPO_ROOT / "frontend" / "app" / "api" / "[...path]" / "route.ts").read_text()
    env_example = (REPO_ROOT / "frontend" / ".env.example").read_text()
    next_config = (REPO_ROOT / "frontend" / "next.config.js").read_text()
    runbook = (REPO_ROOT / "docs" / "sidira-domain-runbook.md").read_text()
    readme = (REPO_ROOT / "README.md").read_text()
    onboarding = (REPO_ROOT / "ONBOARDING.md").read_text()
    deploy_readme = (REPO_ROOT / "deploy" / "README.md").read_text()
    amplify = (REPO_ROOT / "amplify.yml").read_text()

    assert 'process.env.NEXT_PUBLIC_API_BASE ?? "/api"' in api_client
    assert "process.env.SIDIRA_API_BASE_INTERNAL" in route
    assert "process.env.SIDIRA_WEB_PROXY_BASIC_AUTH" in route
    assert "process.env.SIDIRA_INTERNAL_API_KEY" not in route
    assert "authorization" in route
    assert "SIDIRA_API_BASE_INTERNAL: process.env.SIDIRA_API_BASE_INTERNAL" in next_config
    assert "SIDIRA_WEB_PROXY_BASIC_AUTH" not in next_config
    assert "SIDIRA_INTERNAL_API_KEY" not in next_config
    assert "X-Sidira-Internal-Key" not in route
    assert "NEXT_PUBLIC_API_BASE=https://api.sidira.ai" not in env_example
    assert "SIDIRA_INTERNAL_API_KEY" not in env_example
    assert 'test -n "$SIDIRA_API_BASE_INTERNAL"' in amplify
    assert "missing SIDIRA_API_BASE_INTERNAL" in amplify
    assert "missing SIDIRA_WEB_PROXY_BASIC_AUTH" in amplify
    assert "missing SIDIRA_INTERNAL_API_KEY" not in amplify
    assert 'printf "SIDIRA_API_BASE_INTERNAL=%s\\n"' in amplify
    assert 'printf "SIDIRA_WEB_PROXY_BASIC_AUTH=%s\\n"' in amplify
    assert "Production browser traffic should use the same-origin Next" in runbook
    assert "backend gateway token" in runbook
    assert "Amplify or Next artifacts" in runbook
    assert "SIDIRA_WEB_PROXY_BASIC_AUTH_HASH" in runbook
    assert "SIDIRA_WEB_PROXY_BASIC_AUTH=<base64 username:password>" in readme
    assert "when Amplify strips the browser" in readme
    assert "SIDIRA_WEB_PROXY_BASIC_AUTH=<base64 username:password>" in onboarding
    assert "backend gateway token in Amplify" in onboarding
    assert "server-side web-proxy Basic Auth credential" in deploy_readme
    assert "Amplify Hosting strips browser Basic Auth" in deploy_readme
    assert "plus `SIDIRA_INTERNAL_API_KEY`" not in onboarding
    assert "This is an alpha-stage gateway-token workaround" not in readme


def test_amplify_passes_clerk_env_to_next_build() -> None:
    amplify = (REPO_ROOT / "amplify.yml").read_text()

    # Amplify exposes console env vars to the build only — the Next runtime
    # never sees them — so the spec must persist both Clerk vars into
    # .env.production for the #149 cutover to actually take effect.
    assert 'printf "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=%s\\n"' in amplify
    assert 'printf "CLERK_SECRET_KEY=%s\\n"' in amplify
    # Both writes stay optional (pre-cutover and preview builds run keyless)…
    assert 'test -z "$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" || printf' in amplify
    assert 'test -z "$CLERK_SECRET_KEY" || printf' in amplify
    # …but a half-set pair builds a broken auth path and must fail the build —
    # pin the full guard including `exit 1`, not just the error message.
    publishable_guard = (
        'test -z "$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" || test -n "$CLERK_SECRET_KEY" || '
        '{ echo "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY set but CLERK_SECRET_KEY missing" >&2; exit 1; }'
    )
    secret_guard = (
        'test -z "$CLERK_SECRET_KEY" || test -n "$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" || '
        '{ echo "CLERK_SECRET_KEY set but NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY missing" >&2; exit 1; }'
    )
    assert publishable_guard in amplify
    assert secret_guard in amplify
    # Guards and writes must run before the Next build consumes .env.production.
    assert amplify.index(publishable_guard) < amplify.index("npm run build")
    assert amplify.index('printf "CLERK_SECRET_KEY=%s\\n"') < amplify.index("npm run build")


def test_frontend_splits_public_site_from_product_app_hosts() -> None:
    middleware = (REPO_ROOT / "frontend" / "middleware.ts").read_text()
    page = (REPO_ROOT / "frontend" / "app" / "page.tsx").read_text()
    layout = (REPO_ROOT / "frontend" / "app" / "layout.tsx").read_text()
    host_helpers = (REPO_ROOT / "frontend" / "lib" / "site-hosts.ts").read_text()
    runbook = (REPO_ROOT / "docs" / "sidira-domain-runbook.md").read_text()

    assert 'PUBLIC_SITE_HOST = "sidira.ai"' in host_helpers
    assert 'APP_HOST = "app.sidira.ai"' in host_helpers
    assert 'WWW_HOST = "www.sidira.ai"' in host_helpers
    assert "isPublicSiteHost(host)" in page
    assert "PublicCompanyHome" in page
    assert "ProductHome" in page
    assert "shouldRedirectProductPathToApp(host, request.nextUrl.pathname)" in middleware
    assert "redirectUrl.hostname = APP_HOST" in middleware
    assert "showProductNav = !isPublicSiteHost(host)" in layout
    assert "`sidira.ai` / `www.sidira.ai`" in runbook
    assert "`app.sidira.ai`" in runbook


def test_public_homepage_copy_does_not_disclose_internal_recipe() -> None:
    page = (REPO_ROOT / "frontend" / "app" / "page.tsx").read_text()

    assert "Validate product bets before you build" in page
    assert "Request access" in page
    assert "Sign in" in page
    assert "reverse-Figma" not in page
    assert "reverse_prd" not in page
    assert "paired sampling" not in page
    assert "confidence interval" not in page
    assert "scoring formula" not in page


def test_app_host_keeps_temporary_basic_auth_until_clerk_lands() -> None:
    middleware = (REPO_ROOT / "frontend" / "middleware.ts").read_text()
    env_example = (REPO_ROOT / "frontend" / ".env.example").read_text()
    runbook = (REPO_ROOT / "docs" / "sidira-domain-runbook.md").read_text()

    assert "TEMPORARY_APP_BASIC_AUTH = process.env.SIDIRA_WEB_PROXY_BASIC_AUTH" in middleware
    assert "isPublicSiteHost(host)" in middleware
    assert "Authorization required" in middleware
    assert '"www-authenticate": "Basic realm=\\"Sidira\\""' in middleware
    assert "Amplify access control can be disabled" in runbook
    assert "temporary app-host Basic Auth" in runbook
    assert "SIDIRA_WEB_PROXY_BASIC_AUTH" in env_example


def test_frontend_clerk_auth_is_env_gated_alongside_basic_auth_fallback() -> None:
    # #32: Clerk auth pages + middleware land, but stay gated on the publishable
    # key so the build is green and the temporary Basic-Auth fallback above keeps
    # working until the keys are configured in each environment.
    middleware = (REPO_ROOT / "frontend" / "middleware.ts").read_text()
    layout = (REPO_ROOT / "frontend" / "app" / "layout.tsx").read_text()
    clerk_lib = (REPO_ROOT / "frontend" / "lib" / "clerk.ts").read_text()
    env_example = (REPO_ROOT / "frontend" / ".env.example").read_text()

    # The key drives the gate everywhere (server middleware + client bundles).
    assert "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" in clerk_lib
    assert "clerkEnabled = " in clerk_lib

    # Middleware swaps to Clerk only when configured; otherwise the Basic-Auth
    # fallback (asserted in the test above) remains the default export.
    assert "clerkMiddleware" in middleware
    assert "clerkEnabled() ? clerkAuthMiddleware : basicAuthMiddleware" in middleware

    # The same-origin /api proxy staples on the server's Basic Auth credential,
    # so the Clerk path must gate /api on a session too — otherwise enabling
    # Clerk would regress /api from gated (pre-Clerk) to open. Returns 401 for
    # API callers rather than redirecting to the sign-in page.
    assert "isApiRoute = createRouteMatcher" in middleware
    assert '"/api(.*)"' in middleware
    assert "apiAuthChallenge" in middleware

    # ClerkProvider wraps the tree only when configured.
    assert "ClerkProvider" in layout
    assert "clerkEnabled() ? (" in layout

    # The auth pages exist and are themselves gated for keyless builds.
    for route in ("sign-in/[[...sign-in]]", "sign-up/[[...sign-up]]", "sso-callback"):
        page = (REPO_ROOT / "frontend" / "app" / route / "page.tsx").read_text()
        assert "clerkEnabled()" in page

    # Onboarding creates an org so #31's organization.created webhook fires.
    callback = (REPO_ROOT / "frontend" / "app" / "sso-callback" / "page.tsx").read_text()
    assert "CreateOrganization" in callback

    # Env example documents both keys and the required Organizations feature.
    assert "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=" in env_example
    assert "CLERK_SECRET_KEY=" in env_example
    assert "Organizations" in env_example
