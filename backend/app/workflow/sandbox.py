# workflow/sandbox.py
import shutil
from typing import List, Optional, Dict, TYPE_CHECKING
import docker

if TYPE_CHECKING:
    from docker.models.containers import Container  # type: ignore[import-not-found]
import tempfile
import os
import asyncio
import uuid
from app.core.logging import logger
from app.core.config import settings

SANDBOX_MEMORY_LIMIT = os.getenv("SANDBOX_MEMORY_LIMIT", "256m")


class CodeSandbox:
    def __init__(self, image: str = "python-sandbox:latest"):
        self.client = docker.from_env()
        self.image = image
        self.container: Optional["Container"] = None
        self.workspace_dir: Optional[str] = None
        self.failed = False
        self.shared_volume = settings.sandbox_shared_volume
        self.shared_volume_source = None
        self.sandbox_volume_name = os.environ.get("SANDBOX_VOLUME_NAME", "")
        os.makedirs(self.shared_volume, exist_ok=True)

    @classmethod
    async def get_all_images(cls) -> List[str]:
        loop = asyncio.get_event_loop()
        client = docker.from_env()
        images = await loop.run_in_executor(None, client.images.list)
        return [tag for img in images for tag in img.tags]

    @classmethod
    async def delete_image(
        cls, image_ref: str, force: bool = False, noprune: bool = False
    ) -> dict:
        loop = asyncio.get_event_loop()
        client = docker.from_env()

        if image_ref == "python-sandbox:latest":
            return {
                "status": "error",
                "message": f"Error: Cannot delete base image 'python-sandbox:latest'",
                "error_type": "DeleteBaseImage",
            }

        try:
            image = await loop.run_in_executor(
                None, lambda: client.images.get(image_ref)
            )
            remove_result = await loop.run_in_executor(
                None, lambda: image.remove(force=force, noprune=noprune)
            )
            return {"status": "success", "deleted": image_ref, "details": remove_result}

        except docker.errors.ImageNotFound:  # type: ignore[attr-defined]
            return {
                "status": "error",
                "message": f"Image not found: {image_ref}",
                "error_type": "ImageNotFound",
            }

        except docker.errors.APIError as e:  # type: ignore[attr-defined]
            return {
                "status": "error",
                "message": f"Docker API Error: {str(e)}",
                "error_type": "APIError",
            }

        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:  # type: ignore[attr-defined]
            # Already handled above, but keep as fallback
            return {
                "status": "error",
                "message": str(e),
                "error_type": type(e).__name__,
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid input in delete_image: {e}")
            return {
                "status": "error",
                "message": f"Invalid input: {str(e)}",
                "error_type": type(e).__name__,
            }
        except Exception as e:
            logger.exception(f"Unexpected error in delete_image")
            raise

    async def __aenter__(self):
        session_id = uuid.uuid4().hex
        self.workspace_dir = os.path.join(self.shared_volume, session_id)
        os.makedirs(self.workspace_dir, exist_ok=True)
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def start(self):
        if self.container:
            return
        if self.image not in await self.get_all_images():
            logger.warning(f"Image {self.image} not found, using default")
            self.image = "python-sandbox:latest"

        if not self.sandbox_volume_name and not self.shared_volume_source:
            self._detect_shared_volume_source()

        volume_source = self.shared_volume_source or self.sandbox_volume_name
        if not volume_source:
            volume_source = "layra_sandbox_volume"
            logger.warning(
                "Sandbox volume source not detected; falling back to layra_sandbox_volume"
            )

        loop = asyncio.get_event_loop()
        self.container = await loop.run_in_executor(
            None,
            lambda: self.client.containers.run(
                image=self.image,
                command="tail -f /dev/null",
                detach=True,
                mem_limit=SANDBOX_MEMORY_LIMIT,
                cpu_period=100000,
                cpu_quota=50000,
                volumes={volume_source: {"bind": "/shared", "mode": "rw"}},
                security_opt=["no-new-privileges"],
                user="1000:1000",
            ),
        )

    def _detect_shared_volume_source(self):
        try:
            container_id = os.environ.get("HOSTNAME")
            if not container_id:
                return
            current = self.client.containers.get(container_id)
            mounts = current.attrs.get("Mounts", [])
            for mount in mounts:
                if mount.get("Destination") != self.shared_volume:
                    continue
                if mount.get("Type") == "volume":
                    self.shared_volume_source = mount.get("Name")
                    return
                if mount.get("Type") == "bind":
                    self.shared_volume_source = mount.get("Source")
                    return
        except (
            docker.errors.APIError,  # type: ignore[attr-defined]
            docker.errors.NotFound,  # type: ignore[attr-defined]
            KeyError,
            AttributeError,
        ) as e:
            logger.warning(f"Failed to detect sandbox volume source: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in _detect_shared_volume_source")
            # Don't raise - this is a non-critical operation

    async def commit(self, repository: str, tag: str = "latest") -> str:
        if not self.container:
            self.failed = True
            raise RuntimeError("No container to commit")

        loop = asyncio.get_event_loop()
        assert self.container is not None
        image = await loop.run_in_executor(
            None,
            lambda: self.container.commit(  # type: ignore[union-attr]
                repository=repository,
                tag=tag,
            ),
        )
        return f"{repository}:{tag}"

    async def execute(
        self,
        code: str,
        inputs: Optional[Dict[str, str]] = None,
        pip: Optional[Dict[str, str]] = None,
        image_url: str = "",
        remove: bool = False,
        timeout: int = 3600,
    ) -> dict:
        if not self.container:
            self.failed = True
            raise RuntimeError("No container running")

        script_name = f"script_{uuid.uuid4().hex}.py"
        assert self.workspace_dir is not None, "workspace_dir not set"
        script_path = os.path.join(self.workspace_dir, script_name)

        with open(script_path, "w") as f:
            if inputs:
                for k, v in inputs.items():
                    if isinstance(v, str):
                        f.write(f"{k} = {v!r}\n")
                    else:
                        f.write(f"{k} = {v}\n")
            f.write("inputs = locals().copy()\n")
            f.write(code + "\n")
            f.write("\nif 'main' in globals() and callable(main):\n    main(inputs)\n")

        workspace_dir = self.workspace_dir
        container_script_path = (
            f"/shared/{os.path.basename(workspace_dir)}/{script_name}"
        )

        commands = []
        if pip:
            pip_cmd = self._generate_pip_command(pip, image_url, remove)
            commands.append(pip_cmd)
        if code:
            commands.append(f"python {container_script_path}")

        try:
            exit_code, output = await self._exec_container(
                " && ".join(commands), timeout
            )
            if exit_code != 0:
                self.failed = True
                raise docker.errors.ContainerError(  # type: ignore[attr-defined]
                    self.container,
                    exit_code,
                    command=commands,
                    image=self.image,
                    stderr=output,
                )
            return {"result": output.strip()}
        except asyncio.TimeoutError:
            self.failed = True
            raise ValueError("Run timed out")

    async def _exec_container(self, command: str, timeout: int):
        loop = asyncio.get_event_loop()

        def _sync_exec():
            assert self.container is not None
            exec_id = self.container.exec_run(cmd=f"sh -c '{command}'", demux=True)
            return exec_id

        exit_code, (stdout, stderr) = await asyncio.wait_for(
            loop.run_in_executor(None, _sync_exec), timeout=timeout
        )

        output = []
        if stdout:
            output.append(stdout.decode())
        if stderr:
            output.append(stderr.decode())
        return exit_code, "\n".join(output)

    def _generate_pip_command(
        self, pip: Dict[str, str], image_url: str, remove: bool
    ) -> str:
        if not pip:
            return ""

        base_cmd = "pip3 uninstall -y" if remove else "pip3 install"
        packages = []

        for package, version in pip.items():
            package = (
                package.replace(" ", "")
                .replace("&", "")
                .replace("\\", "")
                .replace("/", "")
            )
            if remove:
                packages.append(package)
            else:
                packages.append(f"{package}=={version}" if version else package)

        cmd = f"{base_cmd} {' '.join(packages)}"

        if image_url and not remove:
            cmd += f" -i {image_url}"

        return cmd + " --no-warn-script-location"

    async def close(self):
        try:
            if self.container:
                loop = asyncio.get_event_loop()
                container = self.container
                await loop.run_in_executor(None, lambda: container.remove(force=True))
                self.container = None
        except (docker.errors.APIError, asyncio.TimeoutError) as e:  # type: ignore[attr-defined]
            logger.error(f"Error during container cleanup: {str(e)}")
