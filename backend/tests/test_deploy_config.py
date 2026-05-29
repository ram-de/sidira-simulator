from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_api_artifact_mount_is_writable_for_run_state() -> None:
    compose = (REPO_ROOT / "deploy" / "docker-compose.api.yml").read_text()

    assert "../local-artifacts:/app/local-artifacts:rw" in compose
    assert "../local-artifacts:/app/local-artifacts:ro" not in compose


def test_ec2_deploy_prepares_artifact_tree_for_container_user() -> None:
    deploy = (REPO_ROOT / "deploy" / "ec2-api-deploy.sh").read_text()

    assert 'CONTAINER_UID="${SIDIRA_CONTAINER_UID:-10001}"' in deploy
    assert 'CONTAINER_GID="${SIDIRA_CONTAINER_GID:-10001}"' in deploy
    assert 'chown -R "${CONTAINER_UID}:${CONTAINER_GID}" "$REPO_DIR/local-artifacts"' in deploy
    assert '-v "$REPO_DIR/local-artifacts:/app/local-artifacts:rw"' in deploy
