# workflow/sandbox.py
import shutil
from typing import List, Optional, Dict
import docker
import tempfile
import os
import asyncio
import uuid
from app.core.logging import logger
from app.core.config import settings


class CodeSandbox:
    def __init__(self, image: str = "python-sandbox:latest"):
        self.client = docker.from_env()
        self.image = image
        self.container: Optional[docker.Container] = None
        self.workspace_dir: Optional[str] = None
        self.failed = False
        self.shared_volume = settings.sandbox_shared_volume
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

        except docker.errors.ImageNotFound:
            return {
                "status": "error",
                "message": f"Image not found: {image_ref}",
                "error_type": "ImageNotFound",
            }

        except docker.errors.APIError as e:
            return {
                "status": "error",
                "message": f"Docker API Error: {str(e)}",
                "error_type": "APIError",
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {str(e)}",
                "error_type": "UnexpectedError",
            }

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

        loop = asyncio.get_event_loop()
        self.container = await loop.run_in_executor(
            None,
            lambda: self.client.containers.run(
                image=self.image,
                command="tail -f /dev/null",
                detach=True,
                mem_limit="100m",
                cpu_period=100000,
                cpu_quota=50000,
                volumes={"layra_sandbox_volume": {"bind": "/shared", "mode": "rw"}},
                security_opt=["no-new-privileges"],
                user="1000:1000",
            ),
        )

    async def commit(self, repository: str, tag: str = "latest") -> str:
        if not self.container:
            self.failed = True
            raise RuntimeError("No container to commit")

        loop = asyncio.get_event_loop()
        image = await loop.run_in_executor(
            None,
            lambda: self.container.commit(
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
        script_path = os.path.join(self.workspace_dir, script_name)

        with open(script_path, "w") as f:
            if inputs:
                for k, v in inputs.items():
                    v = repr(v) if v == "" else v
                    f.write(f"{k} = {v}\n")
            f.write(code + "\n")

        container_script_path = (
            f"/shared/{os.path.basename(self.workspace_dir)}/{script_name}"
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
                raise docker.errors.ContainerError(
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
                await loop.run_in_executor(
                    None, lambda: self.container.remove(force=True)
                )
                self.container = None
        except (docker.errors.APIError, asyncio.TimeoutError) as e:
            logger.error(f"Error during container cleanup: {str(e)}")
