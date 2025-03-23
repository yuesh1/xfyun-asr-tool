#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科大讯飞语音转写API上传插件
用于上传音频或视频文件到科大讯飞语音转写服务
"""
import os
import time
import hashlib
import base64
import json
import requests
import tempfile
from moviepy.editor import VideoFileClip

class SliceIdGenerator:
    """生成上传分片ID的工具类"""
    def __init__(self):
        self.__ch = 'aaaaaaaaa`'
        
    def get_next_slice_id(self):
        """获取下一个分片ID"""
        ch = self.__ch
        j = len(ch) - 1
        while j >= 0:
            cj = ch[j]
            if cj != 'z':
                ch = ch[:j] + chr(ord(cj) + 1) + ch[j+1:]
                break
            else:
                ch = ch[:j] + 'a' + ch[j+1:]
                j -= 1
        self.__ch = ch
        return ch


class XfyunASRUpload:
    """科大讯飞语音转写API上传封装类"""
    def __init__(self, app_id, secret_key):
        """
        初始化
        
        Args:
            app_id: 科大讯飞开放平台应用ID
            secret_key: 应用密钥
        """
        self.app_id = app_id
        self.secret_key = secret_key
        self.base_url = "https://raasr.xfyun.cn/api"
        
    def _generate_signature(self):
        """
        生成API调用签名
        
        Returns:
            tuple: (signature, timestamp)
        """
        # 当前时间戳，13位
        timestamp = str(int(time.time() * 1000))
        # 拼接字符串
        base_string = self.app_id + timestamp
        # 使用应用密钥生成hmac-sha1签名
        signature = hashlib.md5(base_string.encode() + self.secret_key.encode()).hexdigest()
        return signature, timestamp
    
    def _generate_params(self, api_name, task_id=None, slice_id=None, file_path=None):
        """
        根据API名称生成请求参数
        
        Args:
            api_name: API名称
            task_id: 任务ID
            slice_id: 分片ID
            file_path: 文件路径
            
        Returns:
            dict: 请求参数字典
        """
        signature, timestamp = self._generate_signature()
        
        params = {
            "app_id": self.app_id,
            "signa": signature,
            "ts": timestamp
        }
        
        if api_name == "prepare":
            # 文件后缀名
            ext = os.path.basename(file_path).split('.')[-1]
            params["file_len"] = os.path.getsize(file_path)
            params["file_name"] = os.path.basename(file_path)
            params["slice_num"] = 1
            # 转写类型，默认为中文
            params["language"] = "cn"
            # 是否开启分词
            params["has_participle"] = "false"
            # 转写结果中最大的候选词个数
            params["max_alternatives"] = 0
            # 开启标点符号
            params["has_seperate"] = "true"
            # 设置多候选词
            params["role_type"] = 2
            # 设置说话人分离，0表示不分离，1表示分离
            params["has_seperate_role"] = "true"
            # 说话人分离人数
            params["speaker_number"] = 2
            # 额外参数
            params["pd"] = "court"
        elif api_name == "upload":
            params["task_id"] = task_id
            params["slice_id"] = slice_id
        elif api_name == "merge":
            params["task_id"] = task_id
        elif api_name == "getProgress":
            params["task_id"] = task_id
        elif api_name == "getResult":
            params["task_id"] = task_id
        
        return params
    
    def _send_request(self, api_name, params, files=None):
        """
        发送HTTP请求
        
        Args:
            api_name: API名称
            params: 请求参数
            files: 文件数据
            
        Returns:
            dict: 响应结果
        """
        url = f"{self.base_url}/{api_name}"
        
        try:
            if files:
                response = requests.post(url, data=params, files=files, timeout=60)
            else:
                response = requests.post(url, data=params, timeout=60)
            
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                return {"ok": False, "err_no": -1, "failed": f"HTTP错误: {response.status_code}"}
            
            result = response.json()
            return result
        except Exception as e:
            print(f"请求异常: {e}")
            return {"ok": False, "err_no": -1, "failed": f"请求异常: {e}"}
    
    def prepare(self, file_path):
        """
        预处理接口
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            str: 任务ID
        """
        params = self._generate_params("prepare", file_path=file_path)
        result = self._send_request("prepare", params)
        
        if result.get("ok") and result.get("data"):
            return result["data"]
        else:
            print(f"预处理失败: {result.get('failed', '未知错误')}")
            return None
    
    def upload(self, task_id, file_path):
        """
        上传文件接口
        
        Args:
            task_id: 任务ID
            file_path: 音频文件路径
            
        Returns:
            bool: 是否上传成功
        """
        slice_id_generator = SliceIdGenerator()
        slice_id = slice_id_generator.get_next_slice_id()
        
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        files = {
            "file": file_content
        }
        
        params = self._generate_params("upload", task_id=task_id, slice_id=slice_id)
        result = self._send_request("upload", params, files)
        
        if result.get("ok"):
            return True
        else:
            print(f"上传失败: {result.get('failed', '未知错误')}")
            return False
    
    def merge(self, task_id, file_path):
        """
        合并文件接口
        
        Args:
            task_id: 任务ID
            file_path: 音频文件路径
            
        Returns:
            bool: 是否合并成功
        """
        params = self._generate_params("merge", task_id=task_id)
        result = self._send_request("merge", params)
        
        if result.get("ok"):
            return True
        else:
            print(f"合并失败: {result.get('failed', '未知错误')}")
            return False
    
    def upload_file(self, file_path):
        """
        上传文件并获取任务ID
        
        Args:
            file_path: 音频或视频文件路径
            
        Returns:
            str: 任务ID
        """
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return None
        
        # 检查文件类型
        file_ext = os.path.splitext(file_path)[1].lower()
        temp_audio_file = None
        
        # 如果是视频文件，提取音频
        if file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.webm']:
            print(f"检测到视频文件，正在提取音频...")
            try:
                # 创建临时文件
                temp_fd, temp_audio_file = tempfile.mkstemp(suffix='.wav')
                os.close(temp_fd)
                
                # 提取音频
                video = VideoFileClip(file_path)
                video.audio.write_audiofile(temp_audio_file, codec='pcm_s16le')
                video.close()
                
                print(f"音频提取完成: {temp_audio_file}")
                file_path = temp_audio_file
            except Exception as e:
                print(f"提取音频失败: {e}")
                if temp_audio_file and os.path.exists(temp_audio_file):
                    os.remove(temp_audio_file)
                return None
        
        # 预处理
        task_id = self.prepare(file_path)
        if not task_id:
            # 如果是临时文件，删除它
            if temp_audio_file and os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            return None
        
        # 上传文件
        if not self.upload(task_id, file_path):
            print("上传文件失败")
            # 如果是临时文件，删除它
            if temp_audio_file and os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            return None
        
        # 合并文件
        if not self.merge(task_id, file_path):
            print("合并文件失败")
            # 如果是临时文件，删除它
            if temp_audio_file and os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            return None
        
        # 如果是临时文件，删除它
        if temp_audio_file and os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)
        
        print("文件上传成功，任务ID:", task_id)
        return task_id


def upload_command(args):
    """上传文件命令处理函数"""
    asr = XfyunASRUpload(args.app_id, args.secret_key)
    task_id = asr.upload_file(args.file_path)
    
    if task_id:
        result = {
            "code": 0,
            "message": "文件上传成功",
            "task_id": task_id
        }
    else:
        result = {
            "code": 1,
            "message": "文件上传失败"
        }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='科大讯飞语音转写API上传工具')
    parser.add_argument('--app_id', required=True, help='科大讯飞应用ID')
    parser.add_argument('--secret_key', required=True, help='应用密钥')
    parser.add_argument('--file_path', required=True, help='音频或视频文件路径')
    
    args = parser.parse_args()
    
    upload_command(args)


if __name__ == '__main__':
    main()


# 用于FastAPI的文件上传处理函数
def handle_upload(file_path, app_id=None, secret_key=None):
    """
    处理上传的文件并返回任务ID
    
    Args:
        file_path: 上传文件的路径
        app_id: 科大讯飞应用ID（可选）
        secret_key: 应用密钥（可选）
        
    Returns:
        str: 任务ID
    """
    # 如果没有提供API凭证，则使用环境变量
    if app_id is None:
        app_id = os.environ.get('XFYUN_APP_ID', 'YOUR_APP_ID')
    if secret_key is None:
        secret_key = os.environ.get('XFYUN_SECRET_KEY', 'YOUR_SECRET_KEY')
    
    # 创建上传实例并处理文件
    asr = XfyunASRUpload(app_id, secret_key)
    task_id = asr.upload_file(file_path)
    
    return task_id
