import os
import uuid
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query
from pydantic import BaseModel, validator

# 导入新版本的讯飞语音识别API
from xfyun_asr_v2 import upload_audio, upload_audio_by_url, get_transcription_result

app = FastAPI()

UPLOAD_DIR = Path('uploads')
UPLOAD_DIR.mkdir(exist_ok=True)

# 定义URL请求模型
class UrlRequest(BaseModel):
    url: str
    app_id: Optional[str] = None
    secret_key: Optional[str] = None
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL必须以http://或https://开头')
        return v

# 定义URL直接上传请求模型
class DirectUrlRequest(BaseModel):
    url: str
    app_id: Optional[str] = None
    secret_key: Optional[str] = None
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL必须以http://或https://开头')
        return v

# 文件上传和URL处理的共同逻辑
async def process_input(input_path, app_id=None, secret_key=None):
    # 使用新版API直接上传文件并获取订单ID
    try:
        # 根据是否提供API凭证调用不同版本的upload_audio
        order_id = upload_audio(input_path, app_id, secret_key)
        return order_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")

# 处理文件上传的端点
@app.post('/upload/file')
async def upload_file(
    file: UploadFile = File(...),
    app_id: str = Form(None),
    secret_key: str = Form(None)
):
    # 生成一个临时ID仅用于文件名
    temp_id = str(uuid.uuid4())
    file_name = file.filename or 'unknown_file'
    file_path = UPLOAD_DIR / f'{temp_id}_{file_name}'
    
    # 保存上传的文件
    with open(file_path, 'wb') as buffer:
        buffer.write(await file.read())
    
    # 处理文件并获取内部任务ID
    task_id = await process_input(str(file_path), app_id, secret_key)
    
    return {'task_id': task_id, 'source_type': 'file', 'file_name': file_name}

# 处理URL的端点
@app.post('/upload/url')
async def upload_url(request: UrlRequest):
    # 生成一个临时ID仅用于文件名
    temp_id = str(uuid.uuid4())
    
    # 从URL获取文件名
    url_path = request.url.split('?')[0]  # 移除查询参数
    file_name = os.path.basename(url_path) or 'url_file'
    file_path = UPLOAD_DIR / f'{temp_id}_{file_name}'
    
    # 下载URL内容
    try:
        response = requests.get(request.url, stream=True, timeout=30)
        response.raise_for_status()  # 确保请求成功
        
        # 保存内容到文件
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        # 处理文件并获取内部任务ID
        task_id = await process_input(str(file_path), request.app_id, request.secret_key)
        
        return {'task_id': task_id, 'source_type': 'url', 'url': request.url}
    except Exception as e:
        # 如果文件已创建但下载失败，删除它
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=f'下载URL内容失败: {str(e)}')

# 处理URL的端点 (直接使用URL外链方式)
@app.post('/upload/direct_url')
async def upload_direct_url(request: DirectUrlRequest):
    try:
        # 直接使用URL外链方式上传到讯飞 API
        task_id = upload_audio_by_url(request.url, request.app_id, request.secret_key)
        
        if not task_id:
            raise HTTPException(status_code=500, detail="上传失败，讯飞 API 返回空任务ID")
            
        return {'task_id': task_id, 'source_type': 'direct_url', 'url': request.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'上传文件失败: {str(e)}')

# 兼容旧版本的上传端点，支持文件上传
@app.post('/upload')
async def upload_legacy(file: UploadFile = File(...), app_id: str = Form(None), secret_key: str = Form(None)):
    return await upload_file(file, app_id, secret_key)

@app.get('/result/{task_id}')
async def get_transcription(
    task_id: str,
    app_id: str = Query(None),
    secret_key: str = Query(None),
    use_cache: bool = Query(True, description="是否使用缓存结果")
):
    try:
        # 使用新版API获取转写结果，传递缓存控制参数
        status, result = get_transcription_result(task_id, app_id, secret_key, use_cache=use_cache)
        
        # 检查状态是否为'not_found'
        if status == 'not_found':
            raise HTTPException(status_code=404, detail='任务不存在')
        
        # 确保返回正确的状态和结果
        return {
            'status': status, 
            'text': result,
            'from_cache': use_cache and status in ['completed', 'failed', 'not_found']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取结果失败: {str(e)}")

@app.get('/')
async def health_check():
    return {'status': 'running'}
