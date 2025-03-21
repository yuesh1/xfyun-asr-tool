# iFLYTEK ASR Tool

A Python tool for interacting with iFLYTEK's Speech Recognition API (科大讯飞语音转写API). This tool allows you to convert audio and video files to text transcripts.

[中文文档](README_xfyun_asr.md) | [使用说明](使用说明.md)

## Features

- Upload audio files to iFLYTEK ASR service
- Extract audio from video files for transcription
- Query transcription progress and retrieve results
- Format transcription results into complete text documents
- Support for speaker separation
- Save formatted transcripts to files
- Batch processing of multiple files

## Prerequisites

1. Register an account on iFLYTEK Open Platform: https://www.xfyun.cn/
2. Create a speech transcription application to get your AppID and Secret Key
3. Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

## Supported Audio Formats

- Formats: wav, flac, opus, m4a, mp3
- Sample rates: 8KHz or 16KHz
- Bit depth: 8bits or 16bits
- Channels: mono or multi-channel
- Size: up to 500MB
- Duration: up to 5 hours (recommended at least 5 minutes)

## Usage

### Upload Audio or Video File

```bash
python xfyun_asr.py upload --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --file_path YOUR_FILE_PATH
```

- Supports direct upload of audio files (wav, flac, opus, m4a, mp3, etc.)
- Supports upload of video files (mp4, avi, mkv, etc.), which will automatically extract the audio track

After successful upload, it will return a task ID (task_id) for subsequent result queries.

### Get Transcription Results

```bash
# Directly query results (if transcription is complete)
python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID

# Wait for transcription to complete and get results
python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --wait

# Custom polling interval and timeout
python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --wait --interval 20 --timeout 7200

# Format results as complete text
python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --format_text

# Save formatted text to file
python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID --format_text --output_file transcript.txt
```

### Process Video Files

For convenience, a dedicated script for processing video files is provided:

```bash
python video_to_text.py --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --video_path VIDEO_PATH --output_dir OUTPUT_DIR --verbose
```

### Batch Processing

Process multiple audio or video files at once:

```bash
python batch_process.py --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --input_dir INPUT_DIR --output_dir OUTPUT_DIR --max_workers 3 --verbose
```

## Using in Your Python Code

```python
from xfyun_asr import XfyunASR

# Initialize
asr = XfyunASR("YOUR_APP_ID", "YOUR_SECRET_KEY")

# Upload file and get task ID
task_id = asr.upload_file("path/to/your/file.mp4")

# Wait for and get results
result = asr.wait_for_result(task_id)

# Format as complete text
full_text = asr.format_transcript_to_text(result)

# Save to file
with open("transcript.txt", "w", encoding="utf-8") as f:
    f.write(full_text)
```

## Notes

1. Free users have a 5-hour usage limit
2. Transcription results are stored for 30 days
3. The same audio file does not need to be uploaded repeatedly; you can use the previous task_id to directly query results
4. Large files are automatically processed in chunks
5. Speaker separation is enabled by default, set to 2 speakers
6. When uploading video files, audio is automatically extracted and temporary files are created, which are automatically deleted after completion
7. The text formatting function organizes transcription results by speaker, displaying them in sections when there are multiple speakers

## Status Codes

Transcription progress status codes:
- 0: Task created successfully
- 1: Audio upload complete
- 2: Audio merge complete
- 3: Audio transcription in progress
- 4: Transcription results being processed
- 5: Transcription complete
- 9: Transcription results upload complete

## Reference

- iFLYTEK Speech Transcription API Documentation: https://www.xfyun.cn/doc/asr/lfasr/API.html

## License

MIT
