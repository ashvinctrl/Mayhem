class DockerClient:
    def build_image(self, dockerfile_path, image_name, tag='latest'):
        """
        Build a Docker image from the specified Dockerfile.

        :param dockerfile_path: Path to the Dockerfile.
        :param image_name: Name of the image to be built.
        :param tag: Tag for the image (default is 'latest').
        """
        pass  # Implementation goes here

    def run_container(self, image_name, container_name, ports=None, env_vars=None):
        """
        Run a Docker container from the specified image.

        :param image_name: Name of the image to run.
        :param container_name: Name to assign to the running container.
        :param ports: Dictionary of ports to expose (default is None).
        :param env_vars: Dictionary of environment variables to set (default is None).
        """
        pass  # Implementation goes here