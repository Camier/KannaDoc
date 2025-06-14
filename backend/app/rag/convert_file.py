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
from app.utils.unoconverter import unoconverter
import asyncio


async def convert_file_to_images(file_content, file_name: str = None):
    """支持多格式文件转换的图片生成函数

    Args:
        file_content: 二进制文件内容
        file_name: 文件名（包含点，如.docx）

    Returns:
        List[BytesIO]: 包含图片数据的字节流列表
    """
    start_time = time.time()
    file_extension = file_name.split(".")[-1]
    # 检查文件类型决定是否需要转换
    if file_extension and file_extension.lower() != "pdf":
        # 其他格式通过 unoserver 转换
        logger.info(f"Converting {file_extension} file via unoserver")
        try:
            # 异步调用转换 (添加输入格式提示)
            pdf_content = await unoconverter.async_convert(
                file_content,
                output_format="pdf",
                input_format=file_extension
            )
            images = convert_from_bytes(pdf_content)
            logger.debug(f"Converted {len(images)} pages from {file_extension} to PDF")
        except Exception as e:
            logger.error(f"Conversion error: {str(e)}")
            raise RuntimeError(f"Document conversion failed: {str(e)}")
    else:
        # 直接处理PDF文件
        logger.info("Processing PDF directly")
        images = convert_from_bytes(file_content)

    # 处理图片到内存缓冲区
    images_buffer = []
    processing_start = time.time()

    try:
        for i, image in enumerate(images):
            buffer = BytesIO()
            image.save(buffer, format="PNG", optimize=True, quality=85)
            buffer.seek(0)
            images_buffer.append(buffer)

            # 及时清理PIL Image对象
            del image

            # 每处理10页记录一次
            if (i + 1) % 10 == 0:
                logger.debug(f"Processed {i+1} pages so far")

    except Exception as e:
        logger.error(f"Image processing failed: {str(e)}")
        # 清理已创建的缓冲区
        for buf in images_buffer:
            buf.close()
        raise

    finally:
        # 显式清理PIL Images列表
        del images

    total_time = time.time() - start_time
    processing_time = time.time() - processing_start
    logger.info(
        f"Successfully converted file to {len(images_buffer)} images | "
        f"Total: {total_time:.2f}s | Processing: {processing_time:.2f}s"
    )
    return images_buffer


async def save_file_to_minio(username: str, uploadfile: UploadFile):
    # 将生成的图像上传到 MinIO
    file_name = f"{username}_{os.path.splitext(uploadfile.filename)[0]}_{ObjectId()}{os.path.splitext(uploadfile.filename)[1]}"
    await async_minio_manager.upload_file(file_name, uploadfile)
    minio_url = await async_minio_manager.create_presigned_url(file_name)
    return file_name, minio_url


async def save_image_to_minio(username, filename, image_stream):
    # 将生成的图像上传到 MinIO
    file_name = f"{username}_{os.path.splitext(filename)[0]}_{ObjectId()}.png"
    await async_minio_manager.upload_image(file_name, image_stream)
    minio_url = await async_minio_manager.create_presigned_url(file_name)
    return file_name, minio_url
