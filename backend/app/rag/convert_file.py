import os
from typing import List
from fastapi import UploadFile
from pdf2image import convert_from_bytes
from app.db.miniodb import async_minio_manager
from bson.objectid import ObjectId
import time
from app.core.logging import logger
from app.core.config import settings
from app.utils.unoconverter import unoconverter
from PIL import Image, ImageSequence
import io

async def convert_file_to_images(
    file_content: bytes,
    file_name: str = None,
    handle_all_frames: bool = False
) -> List[io.BytesIO]:
    """支持多格式文件转换的图片生成函数，可选择处理动图的所有帧
    
    Args:
        file_content: 二进制文件内容
        file_name: 文件名（包含点，如.docx）
        handle_all_frames: 是否处理动图的所有帧（True=所有帧，False=仅第一帧）
    
    Returns:
        List[BytesIO]: 包含图片数据的字节流列表
    """
    start_time = time.time()
    file_extension = file_name.split(".")[-1].lower() if file_name else ""
    
    # 定义支持的图片格式（不包括svg）
    image_extensions = [
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 
        'ico', 'tiff', 'tif', 'dib', 'jfif', 'pjpeg', 'pjp'
    ]
    
    # 检查文件类型决定处理方式
    if file_extension in image_extensions:
        # 直接处理图片文件
        logger.info(f"Processing image file directly: {file_extension}")
        try:
            images = []
            with Image.open(io.BytesIO(file_content)) as img:
                # 处理多帧图片（如GIF, TIFF, WEBP等）
                if hasattr(img, 'is_animated') and img.is_animated and handle_all_frames:
                    for frame in ImageSequence.Iterator(img):
                        # 转换为RGB并调整大小
                        frame = frame.convert('RGB')
                        frame = resize_image_to_a4(frame)
                        images.append(frame.copy())
                else:
                    # 单帧图片处理（包括动图的第一帧）
                    if img.mode in ('RGBA', 'P', 'LA', 'CMYK'):
                        img = img.convert('RGB')
                    img = resize_image_to_a4(img)
                    images.append(img)
            
            logger.debug(f"Processed {len(images)} frames from image")

        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
            raise RuntimeError(f"Image processing failed: {str(e)}")
    
    elif file_extension == "pdf":
        # 直接处理PDF文件
        logger.info("Processing PDF directly")
        images = convert_from_bytes(file_content, dpi=int(settings.embedding_image_dpi))
    
    elif file_extension:  # 其他格式（含svg）
        # 通过 unoserver 转换
        logger.info(f"Converting {file_extension} file via unoserver")
        try:
            pdf_content = await unoconverter.async_convert(
                file_content,
                output_format="pdf",
                input_format=file_extension
            )
            images = convert_from_bytes(pdf_content, dpi=int(settings.embedding_image_dpi))
            logger.debug(f"Converted {len(images)} pages from {file_extension} to PDF")
        except Exception as e:
            logger.error(f"Conversion error: {str(e)}")
            raise RuntimeError(f"Document conversion failed: {str(e)}")
    
    else:
        raise ValueError("Unsupported file type")

    # 处理图片到内存缓冲区
    images_buffer = []
    processing_start = time.time()

    try:
        for i, image in enumerate(images):
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            images_buffer.append(buffer)

            # 及时清理PIL Image对象
            del image

            if (i + 1) % 10 == 0:
                logger.debug(f"Processed {i+1} pages so far")
    
    except Exception as e:
        logger.error(f"Image processing failed: {str(e)}")
        for buf in images_buffer:
            buf.close()
        raise
    
    finally:
        del images  # 显式清理PIL Images列表

    total_time = time.time() - start_time
    processing_time = time.time() - processing_start
    logger.info(
        f"Successfully converted file to {len(images_buffer)} images | "
        f"Total: {total_time:.2f}s | Processing: {processing_time:.2f}s"
    )
    return images_buffer

def resize_image_to_a4(image: Image.Image) -> Image.Image:
    """调整图片尺寸，长边不超过A4长度（100dpi下1169像素）"""
    # 计算A4尺寸（100dpi: 8.27x11.69英寸）
    max_pixels = int(11.69*int(settings.embedding_image_dpi))  # 100dpi: 11.69*100 ≈ 1169
    
    # 获取原始尺寸
    width, height = image.size
    
    # 检查是否需要调整
    if max(width, height) <= max_pixels:
        return image
    
    # 计算新尺寸（保持宽高比）
    if width > height:
        new_width = max_pixels
        new_height = int(height * (max_pixels / width))
    else:
        new_height = max_pixels
        new_width = int(width * (max_pixels / height))
    
    # 使用高质量滤波器调整大小
    return image.resize((new_width, new_height), Image.LANCZOS)


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
