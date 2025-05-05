# workflow/sandbox.py
import docker
import tempfile
import os
import asyncio
import uuid


class CodeSandbox:
    def __init__(self):
        self.client = docker.from_env()
        self.image = "python-sandbox:latest"
        self.container = None
        self.tmpdir = None  # 延迟初始化

    async def __aenter__(self):
        # 延迟创建临时目录
        self.tmpdir = tempfile.TemporaryDirectory()
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
    
    async def start(self):
        """启动长期运行的容器"""
        if self.container:
            return
            
        loop = asyncio.get_event_loop()
        self.container = await loop.run_in_executor(
            None,
            lambda: self.client.containers.run(
                image=self.image,
                command="tail -f /dev/null",  # 保持容器运行
                detach=True,
                mem_limit="100m",
                cpu_period=100000,
                cpu_quota=50000,
                volumes={self.tmpdir.name: {"bind": "/app", "mode": "rw"}},
                # network_mode="none",
                security_opt=["no-new-privileges"],
                user="restricted_user"
            )
        )

    async def execute(self, code: str, inputs: dict = None, pip: dict = None, image_url: str = "", remove: bool = False, timeout: int = 60) -> dict:
        """在持久化容器中执行代码"""
        if not self.container:
            raise RuntimeError("No container running")

        # 生成唯一脚本文件名
        script_name = f"script_{uuid.uuid4().hex}.py"
        script_path = os.path.join(self.tmpdir.name, script_name)

        # 写入脚本文件
        with open(script_path, "w") as f:
            if inputs:
                for k, v in inputs.items():
                    v = "''" if v == "" else v
                    f.write(f"{k} = {v}\n")
            f.write(code + "\n")
            if inputs:
                f.write('print("####Global variable updated####")\n')
                for k in inputs:
                    f.write(f'{k} = "\'\'" if {k}=="" else {k}\n')
                    f.write(f'print("{k} =", {k})\n')

        # 构建完整命令链
        commands = []
        if pip:
            pip_cmd = self._generate_pip_command(pip, image_url, remove)
            commands.append(pip_cmd)
        if code:
            commands.append(f"python /app/{script_name}")
        
        try:
            # 在容器内执行命令链
            exit_code, output = await self._exec_container(" && ".join(commands), timeout)
            if exit_code != 0:
                raise docker.errors.ContainerError(
                    self.container,
                    exit_code,
                    command=commands,
                    image=self.image,
                    stderr=output
                )
            return {"result": output.strip()}
        except asyncio.TimeoutError:
            raise ValueError("Run timed out")

    async def _exec_container(self, command: str, timeout: int):
        """在运行中的容器执行命令"""
        loop = asyncio.get_event_loop()
        
        def _sync_exec():
            exec_id = self.container.exec_run(
                cmd=f"sh -c '{command}'",
                demux=True  # 分离stdout/stderr
            )
            return exec_id
        
        # 异步执行
        exit_code, (stdout, stderr) = await asyncio.wait_for(
            loop.run_in_executor(None, _sync_exec),
            timeout=timeout
        )
        
        # 处理输出
        output = []
        if stdout: output.append(stdout.decode())
        if stderr: output.append(stderr.decode())
        return exit_code, "\n".join(output)

    def _generate_pip_command(self, pip: dict, image_url: str, remove: bool) -> str:
        """生成pip安装/卸载命令"""
        if not pip:
            return ""
        
        base_cmd = "pip3 uninstall -y" if remove else "pip3 install"
        packages = []
        
        for package, version in pip.items():
            if remove:
                packages.append(package)
            else:
                packages.append(f"{package}=={version}" if version else package)
        
        cmd = f"{base_cmd} {' '.join(packages)}"
        
        if image_url and not remove:
            cmd += f" -i {image_url}"
        
        return cmd + " --no-warn-script-location"

    async def close(self):
        """清理资源（由上下文管理器自动调用）"""
        if self.container:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.container.remove(force=True))
            self.container = None
        if self.tmpdir:
            self.tmpdir.cleanup()


# async def run():
#     async with CodeSandbox() as sandbox:
#         # 首次执行（自动安装依赖）
#         result1 = await sandbox.execute(
#             code="",
#             pip={"requests": ""},
#             image_url="https://pypi.tuna.tsinghua.edu.cn/simple"
#         )

#         # 后续执行复用环境
#         result2 = await sandbox.execute(
#             code="import requests; print(requests.__version__)"
#         )
#         return result1,result2

# print(asyncio.run(run()))