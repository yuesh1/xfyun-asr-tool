# 科大讯飞语音转写API工具

这个工具提供了与科大讯飞语音转写API交互的功能，包含两个主要插件：
1. 文件上传插件 - 上传音频文件到科大讯飞服务器
2. 查询结果插件 - 获取转写结果

## 功能特点

- 支持音频文件上传和分片处理
- 支持查询转写进度和获取转写结果
- 支持说话人分离功能
- 支持提取视频中的音频进行转写
- 支持将转写结果格式化为完整文本
- 支持将格式化后的文本保存到文件
- 提供完整的命令行接口
- 返回标准化的JSON格式结果

## 使用前提

1. 注册科大讯飞开放平台账号：https://www.xfyun.cn/
2. 创建语音转写应用，获取AppID和Secret Key
3. 安装必要的Python依赖：

   ```bash
   pip install requests
   pip install moviepy  # 用于处理视频文件
   ```

## 支持的音频格式

- 格式：wav, flac, opus, m4a, mp3
- 采样率：8KHz或16KHz
- 位长：8bits或16bits
- 声道：单声道或多声道
- 大小：不超过500MB
- 时长：不超过5小时（建议5分钟以上）

## 使用方法

### 上传音频或视频文件

```bash
python xfyun_asr.py upload --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --file_path YOUR_FILE_PATH
```

- 支持直接上传音频文件（wav, flac, opus, m4a, mp3等）
- 支持上传视频文件（mp4, avi, mkv等），会自动提取音频轨道

成功上传后，将返回任务ID（task_id），用于后续查询结果。

### 查询转写结果

```bash
# 直接查询结果（如果转写已完成）
python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID

# 等待转写完成并获取结果
python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --wait

# 自定义轮询间隔和超时时间
python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --wait --interval 20 --timeout 7200

# 将结果格式化为完整文本
python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --format_text

# 将格式化后的文本保存到文件
python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --format_text --output_file transcript.txt
```

## 返回结果格式

### 上传文件返回格式

```json
{
  "code": 0,
  "message": "文件上传成功",
  "task_id": "383e72a47557490aa05a344074117a9d"
}
```

### 获取结果返回格式

```json
{
  "code": 0,
  "message": "获取结果成功",
  "data": [
    {
      "bg": "0",
      "ed": "4950",
      "onebest": "科大讯飞是中国的智能语音技术提供商。",
      "speaker": "0"
    },
    {
      "bg": "5000",
      "ed": "9800",
      "onebest": "语音转写服务可以将语音转换为文字。",
      "speaker": "1"
    }
  ],
  "full_text": "说话人 0：科大讯飞是中国的智能语音技术提供商。\n\n说话人 1：语音转写服务可以将语音转换为文字。"
}
```

## 注意事项

1. 免费用户有5小时的使用时长限制
2. 转写结果保存时长为30天
3. 同一个音频文件不需要重复上传，可以使用之前的task_id直接查询结果
4. 上传大文件时会自动进行分片处理
5. 默认开启说话人分离功能，设置为2个说话人
6. 上传视频文件时，会自动提取音频并创建临时文件，完成后会自动删除临时文件
7. 格式化文本功能会按说话人分组整理转写结果，多个说话人时会分段显示

## 状态码说明

转写进度状态码含义：
- 0: 任务创建成功
- 1: 音频上传完成
- 2: 音频合并完成
- 3: 音频转写中
- 4: 转写结果处理中
- 5: 转写完成
- 9: 转写结果上传完成

## 参考文档

- 科大讯飞语音转写API文档：https://www.xfyun.cn/doc/asr/lfasr/API.html
