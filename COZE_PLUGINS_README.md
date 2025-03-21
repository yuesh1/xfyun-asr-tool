# 科大讯飞语音转写API Coze插件

这个项目包含两个为Coze平台开发的插件，用于使用科大讯飞语音转写API将音频和视频文件转写为文本。

## 插件1: 文件上传插件 (xfyun_asr_upload.py)

这个插件负责上传音频或视频文件到科大讯飞语音转写服务，并返回任务ID。

### 功能特点

- 支持上传音频文件（wav, flac, opus, m4a, mp3等）
- 支持上传视频文件（mp4, avi, mov, mkv等），自动提取音频轨道
- 自动处理大文件分片上传
- 返回任务ID，用于后续查询转写结果

### 使用方法

```bash
python xfyun_asr_upload.py --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --file_path YOUR_FILE_PATH
```

### 返回格式

```json
{
  "code": 0,
  "message": "文件上传成功",
  "task_id": "TASK_ID"
}
```

## 插件2: 结果查询插件 (xfyun_asr_result.py)

这个插件负责查询转写结果，并可以将结果格式化为完整文本。

### 功能特点

- 查询转写进度和结果
- 支持等待转写完成
- 将转写结果格式化为完整文本
- 支持按说话人分组
- 可以将结果保存到文件

### 使用方法

```bash
# 查询结果
python xfyun_asr_result.py --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID

# 等待转写完成并查询结果
python xfyun_asr_result.py --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --wait

# 格式化为完整文本
python xfyun_asr_result.py --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --format_text

# 保存到文件
python xfyun_asr_result.py --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --format_text --output_file transcript.txt
```

### 返回格式

```json
{
  "code": 0,
  "message": "获取转写结果成功",
  "formatted_text": "格式化后的文本内容..."
}
```

## 在Coze平台上配置插件

### 上传插件配置

1. 创建新插件
2. 名称：科大讯飞语音转写上传
3. 描述：上传音频或视频文件到科大讯飞语音转写服务
4. 参数配置：
   - app_id：科大讯飞应用ID
   - secret_key：应用密钥
   - file_path：音频或视频文件路径
5. 返回格式：JSON

### 结果查询插件配置

1. 创建新插件
2. 名称：科大讯飞语音转写结果查询
3. 描述：查询科大讯飞语音转写结果并格式化文本
4. 参数配置：
   - app_id：科大讯飞应用ID
   - secret_key：应用密钥
   - task_id：转写任务ID
   - wait：是否等待转写完成（布尔值）
   - format_text：是否格式化为完整文本（布尔值）
5. 返回格式：JSON

## 使用流程

1. 使用上传插件上传文件，获取任务ID
2. 使用结果查询插件查询转写结果
3. 可以选择等待转写完成，并将结果格式化为完整文本

## 注意事项

1. 需要在科大讯飞开放平台注册账号并创建应用
2. 免费用户有5小时的使用限制
3. 转写结果保存30天
4. 同一个音频文件不需要重复上传，可以使用之前的任务ID直接查询结果
5. 视频文件会自动提取音频，处理完成后临时文件会自动删除
