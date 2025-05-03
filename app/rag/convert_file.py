from io import BytesIO
import os
import tempfile
import asyncio
from fastapi import UploadFile
from pdf2image import convert_from_bytes
from app.db.miniodb import async_minio_manager
from bson.objectid import ObjectId
import time
from app.core.logging import logger


async def convert_file_to_images(file_content, file_name: str = None):
    """支持多格式文件转换的图片生成函数

    Args:
        file_content: 二进制文件内容
        file_name: 文件名（包含点，如.docx）

    Returns:
        List[BytesIO]: 包含图片数据的字节流列表
    """
    file_extension = file_name.split(".")[-1]
    # 检查文件类型决定是否需要转换
    if file_extension and file_extension.lower() != "pdf":
        logger.info(f"开始转换 {file_extension} 文件到PDF")
        tmp_input_path = None
        try:
            # 创建临时输入文件
            with tempfile.NamedTemporaryFile(
                suffix=file_extension, delete=False, prefix="convert_input_"
            ) as tmp_input:
                tmp_input.write(file_content)
                tmp_input_path = tmp_input.name

            # 创建临时输出目录
            with tempfile.TemporaryDirectory(prefix="libreoffice_") as tmp_output:
                # 执行LibreOffice转换命令
                cmd = [
                    "libreoffice",
                    "--headless",
                    "--nologo",
                    "--nofirststartwizard",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    tmp_output,
                    tmp_input_path,
                ]

                # 异步执行转换命令
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    raise RuntimeError(f"文件转换失败: {stderr.decode()}")

                # 查找生成的PDF文件
                pdf_files = [f for f in os.listdir(tmp_output) if f.endswith(".pdf")]
                if not pdf_files:
                    raise RuntimeError("未生成PDF文件")

                # 读取转换后的PDF内容
                with open(os.path.join(tmp_output, pdf_files[0]), "rb") as f:
                    pdf_content = f.read()

                # 转换PDF为图片
                images = convert_from_bytes(pdf_content)
        finally:
            # 确保删除临时输入文件
            if tmp_input_path and os.path.exists(tmp_input_path):
                os.unlink(tmp_input_path)
                logger.debug(f"已清理临时输入文件: {tmp_input_path}")
    else:
        # 直接处理PDF文件
        logger.info("直接处理PDF文件")
        images = convert_from_bytes(file_content)

    # 处理图片到内存缓冲区
    images_buffer = []
    time_start = time.time()

    try:
        for i, image in enumerate(images):
            buffer = BytesIO()
            image.save(buffer, format="PNG", optimize=True, quality=85)
            buffer.seek(0)
            images_buffer.append(buffer)

            # 及时清理PIL Image对象
            del image

    except Exception as e:
        logger.error(f"图片处理失败: {str(e)}")
        # 清理已创建的缓冲区
        for buf in images_buffer:
            buf.close()
        raise

    finally:
        # 显式清理PIL Images列表
        del images

    logger.info(
        f"成功转换文件为 {len(images_buffer)} 张图片，耗时 {time.time() - time_start:.2f}s"
    )
    return images_buffer


async def save_file_to_minio(username: str, uploadfile: UploadFile):
    # 将生成的图像上传到 MinIO
    file_name = f"{username}_{os.path.splitext(uploadfile.filename)[0]}_{ObjectId()}{os.path.splitext(uploadfile.filename)[1]}"
    await async_minio_manager.upload_file(file_name, uploadfile)
    minio_url = await async_minio_manager.create_presigned_url(file_name)

    # minio_url = minio_url.replace("localhost:9110", "192.168.1.5:9110")
    # minio_url = minio_url.replace("localhost:9110", "127.0.0.1:9110")
    return file_name, minio_url


async def save_image_to_minio(username, filename, image_stream):
    # 将生成的图像上传到 MinIO
    file_name = f"{username}_{os.path.splitext(filename)[0]}_{ObjectId()}.png"
    await async_minio_manager.upload_image(file_name, image_stream)
    minio_url = await async_minio_manager.create_presigned_url(file_name)

    # minio_url = minio_url.replace("localhost:9110", "192.168.1.5:9110")
    # minio_url = minio_url.replace("localhost:9110", "127.0.0.1:9110")
    return file_name, minio_url
