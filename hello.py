import requests
import argparse
import json

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Transcribe audio from a URL using 302ai API')
    parser.add_argument('--api_key', required=True, help='Your 302ai API key')
    parser.add_argument('--audio_url', required=True, help='URL to the audio file to transcribe')
    parser.add_argument('--model', default='whisper-1', help='Model to use for transcription')
    parser.add_argument('--temperature', default='0', help='Temperature for the model')
    parser.add_argument('--language', help='Language of the audio (optional)')
    parser.add_argument('--prompt', help='Prompt to guide the transcription (optional)')
    
    args = parser.parse_args()
    
    api_key = args.api_key
    audio_url = args.audio_url
     # 首先下载音频文件内容
    try:
        print("正在下载音频文件...")
        audio_response = requests.get(audio_url, stream=True)
        audio_response.raise_for_status()  # 检查下载是否成功
        
        # 使用 BytesIO 将下载内容转为类似文件对象处理
        audio_file = {"file": ("audio.mp3", audio_response.content)}
        
    except requests.exceptions.RequestException as e:
        print(f"下载音频失败: {e}")
        result = {"message": "下载文件失败！", "code": 400}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    # 构建 API 请求参数
    api_url = "https://api.302ai.cn/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    data = {
        "model": args.model,
        "response_format": "json",
        "temperature": args.temperature,
    }
    # 添加可选参数（如果提供）
    if args.prompt:
        data["prompt"] = args.prompt
    if args.language:
        data["language"] = args.language
    try:
        print("正在发送 API 请求...")
        response = requests.post(
            api_url,
            headers=headers,
            data=data,
            files=audio_file  # 重点：将音频文件作为文件上传
        )
        response.raise_for_status()
        result = {"message": "Success!", "code": 200, "content": response.json()}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    except requests.exceptions.RequestException as e:
            print(f"API 调用失败: {e}")
            if response.text:
                print("服务器返回的错误信息:", response.text)
            result = {"message": f"服务器返回的错误信息:{response.text}", "code": 400}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result

    result = {"message": "Hello, world!"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    main()