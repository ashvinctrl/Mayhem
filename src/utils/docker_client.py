"""Docker SDK client for container-level chaos operations."""
import logging

logger = logging.getLogger(__name__)

try:
    import docker
    _docker_available = True
except ImportError:
    _docker_available = False
    logger.warning("docker package not installed — container operations unavailable. Run: pip install docker")


class DockerClient:
    """Thin wrapper around the Docker SDK for chaos operations."""

    def __init__(self):
        self._client = None
        if _docker_available:
            try:
                self._client = docker.from_env()
                self._client.ping()
            except Exception as e:
                logger.warning(f"Docker daemon not accessible: {e}")
                self._client = None

    @property
    def available(self):
        return self._client is not None

    def build_image(self, dockerfile_path, image_name, tag='latest'):
        if not self._client:
            raise RuntimeError("Docker not available")
        image, logs = self._client.images.build(path=dockerfile_path, tag=f"{image_name}:{tag}")
        return image

    def run_container(self, image_name, container_name, ports=None, env_vars=None):
        if not self._client:
            raise RuntimeError("Docker not available")
        return self._client.containers.run(
            image_name,
            name=container_name,
            ports=ports or {},
            environment=env_vars or {},
            detach=True
        )

    def restart_container(self, container_name, timeout=10):
        """Restart a container. Returns new status string."""
        if not self._client:
            raise RuntimeError("Docker not available")
        container = self._client.containers.get(container_name)
        container.restart(timeout=timeout)
        container.reload()
        return container.status

    def pause_container(self, container_name):
        """Pause (freeze) a container."""
        if not self._client:
            raise RuntimeError("Docker not available")
        self._client.containers.get(container_name).pause()

    def unpause_container(self, container_name):
        """Unpause a previously frozen container."""
        if not self._client:
            raise RuntimeError("Docker not available")
        self._client.containers.get(container_name).unpause()

    def list_containers(self, all=False):
        """List containers as plain dicts."""
        if not self._client:
            return []
        return [
            {
                "name": c.name,
                "id": c.short_id,
                "status": c.status,
                "image": c.image.tags,
            }
            for c in self._client.containers.list(all=all)
        ]

    def get_container_stats(self, container_name):
        """Return a single stats snapshot for a container."""
        if not self._client:
            return {}
        return self._client.containers.get(container_name).stats(stream=False)
