# workflow/sandbox.py
import docker
import tempfile
import os
import asyncio


class CodeSandbox:
    def __init__(self):
        self.client = docker.from_env()
        self.image = "python-sandbox:latest"

    async def execute(self, code: str, inputs: dict, pip: dict, image_url: str = "", remove: bool = False, timeout: int = 10) -> dict:
        """在沙箱中执行代码"""
        container = None  # 初始化container变量
        with tempfile.TemporaryDirectory() as tmpdir:
            # 生成执行文件
            script_path = os.path.join(tmpdir, "script.py")
            with open(script_path, "w") as f:
                if len(inputs):
                    for k, v in inputs.items():
                        v = "''" if v == "" else v
                        f.write(f"{k}={v}\n")
                f.write(code + "\n")
                if len(inputs):
                    f.write(f'print("####Global variable updated####")\n')
                    for k, v in inputs.items():
                        f.write(f'{k} = "\'\'" if {k}=="" else {k}\n')
                        f.write(f'print("{k} =",{k})\n')

            try:
                # 异步执行容器
                container = await self._run_pip(pip, image_url, remove)
                result_pip = await asyncio.wait_for(
                    self._get_result(container), timeout=timeout
                )
                container = await self._run_container(tmpdir)
                result = await asyncio.wait_for(
                    self._get_result(container), timeout=timeout
                )
                return result
            except asyncio.TimeoutError:
                raise ValueError("执行超时")
            finally:
                if container:
                    await self._remove_container(container)

    async def _run_container(self, tmpdir: str):
        """异步启动容器"""
        loop = asyncio.get_event_loop()
        container = await loop.run_in_executor(
            None,
            lambda: self.client.containers.run(
                image=self.image,
                command="python /app/script.py",
                detach=True,
                mem_limit="100m",
                cpu_period=100000,
                cpu_quota=50000,
                volumes={tmpdir: {"bind": "/app", "mode": "ro"}},
                network_mode="none",
                security_opt=["no-new-privileges"],
                user="restricted_user",
                stdout=True,
                stderr=True,
            ),
        )
        return container

    async def _run_pip(self, pip: dict, image_url: str = "", remove: bool = False):
        """异步启动容器"""
        if remove:
            cmd = "pip3 uninstall"
        else:
            cmd = "pip3 install"
        for package, version in pip.items():
            if version:
                cmd += f" {package}=={version}"
            else:
                cmd += f" {package}"
        if image_url:
            cmd += f" -i {image_url}"
        loop = asyncio.get_event_loop()
        container = await loop.run_in_executor(
            None,
            lambda: self.client.containers.run(
                image=self.image,
                command=cmd,
                detach=True,
                mem_limit="100m",
                cpu_period=100000,
                cpu_quota=50000,
                network_mode="none",
                security_opt=["no-new-privileges"],
                user="restricted_user",
                stdout=True,
                stderr=True,
            ),
        )
        return container

    async def _get_result(self, container):
        """异步获取执行结果"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, container.wait)
            if result["StatusCode"] != 0:
                logs = await loop.run_in_executor(None, container.logs)
                logs = logs.decode()
                raise docker.errors.ContainerError(
                    container,
                    result["StatusCode"],
                    command="python script.py",
                    image=self.image,  # 使用预定义的镜像名称
                    stderr=logs,
                )

            output = await loop.run_in_executor(None, container.logs)
            output = output.decode().strip()
            return {"result": output}
        except docker.errors.APIError as e:
            raise ValueError(f"Docker API错误: {str(e)}")

    async def _remove_container(self, container):
        """异步移除容器"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: container.remove(force=True))
