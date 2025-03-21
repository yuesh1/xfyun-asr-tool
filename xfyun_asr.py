#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科大讯飞语音转写API插件
包含两个主要功能：
1. 文件上传 - 上传音频文件到科大讯飞服务器
2. 查询结果 - 获取转写结果

使用方法：
1. 上传文件：python xfyun_asr.py upload --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --file_path YOUR_AUDIO_FILE_PATH
2. 查询结果：python xfyun_asr.py get_result --app_id YOUR_APP_ID --secret_key YOUR_SECRET_KEY --task_id YOUR_TASK_ID

注意：
- 支持的音频格式：wav, flac, opus, m4a, mp3
- 音频大小不超过500M
- 音频时长不超过5小时，建议5分钟以上
- 支持语言：中文普通话、英语等
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import time
import sys
import tempfile
import requests

# 尝试不同的moviepy导入方式
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
    except ImportError:
        print("警告: 无法导入VideoFileClip，视频文件处理功能将不可用")
        VideoFileClip = None

# 科大讯飞语音转写API主机地址
LFASR_HOST = 'http://raasr.xfyun.cn/api'

# API接口路径
API_PREPARE = '/prepare'
API_UPLOAD = '/upload'
API_MERGE = '/merge'
API_GET_PROGRESS = '/getProgress'
API_GET_RESULT = '/getResult'

# 文件分片大小（10MB）
FILE_PIECE_SIZE = 10 * 1024 * 1024


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
                j = j - 1
        self.__ch = ch
        return self.__ch


class XfyunASR:
    """科大讯飞语音转写API封装类"""
    
    def __init__(self, app_id, secret_key):
        """
        初始化
        
        Args:
            app_id: 科大讯飞开放平台应用ID
            secret_key: 应用密钥
        """
        self.app_id = app_id
        self.secret_key = secret_key
    
    def _generate_signature(self):
        """
        生成API调用签名
        
        Returns:
            tuple: (signature, timestamp)
        """
        # 获取当前时间戳
        ts = str(int(time.time()))
        
        # 计算baseString的MD5值
        m = hashlib.md5()
        m.update((self.app_id + ts).encode('utf-8'))
        md5_str = m.hexdigest()
        md5_bytes = md5_str.encode('utf-8')
        
        # 使用secret_key对MD5值进行HMAC-SHA1加密
        signa = hmac.new(self.secret_key.encode('utf-8'), md5_bytes, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = signa.decode('utf-8')
        
        return signa, ts
    
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
        # 生成签名和时间戳
        signa, ts = self._generate_signature()
        
        # 构建基本参数
        params = {
            'app_id': self.app_id,
            'signa': signa,
            'ts': ts
        }
        
        # 根据不同API添加特定参数
        if api_name == API_PREPARE and file_path:
            file_len = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            # 计算分片数量
            slice_num = int(file_len / FILE_PIECE_SIZE) + (0 if (file_len % FILE_PIECE_SIZE == 0) else 1)
            
            params.update({
                'file_len': str(file_len),
                'file_name': file_name,
                'slice_num': str(slice_num),
                'has_seperate': 'true',  # 开启说话人分离
                'speaker_number': '2',   # 默认设置为2个说话人
                'lfasr_type': '0'        # 标准版
            })
        
        elif api_name == API_UPLOAD and task_id and slice_id:
            params.update({
                'task_id': task_id,
                'slice_id': slice_id
            })
        
        elif api_name == API_MERGE and task_id and file_path:
            params.update({
                'task_id': task_id,
                'file_name': os.path.basename(file_path)
            })
        
        elif (api_name == API_GET_PROGRESS or api_name == API_GET_RESULT) and task_id:
            params.update({
                'task_id': task_id
            })
        
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
        url = LFASR_HOST + api_name
        
        # 设置请求头
        headers = None
        if api_name != API_UPLOAD:
            headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        
        # 发送请求
        response = requests.post(url, data=params, files=files, headers=headers)
        
        # 解析响应
        try:
            result = json.loads(response.text)
            if result.get('ok') == 0:
                return result
            else:
                error_msg = result.get('failed', '未知错误')
                print(f"API调用失败: {error_msg}")
                return result
        except Exception as e:
            print(f"解析响应失败: {e}")
            print(f"原始响应: {response.text}")
            return {'ok': -1, 'err_no': -1, 'failed': str(e), 'data': None}
    
    def prepare(self, file_path):
        """
        预处理接口
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            str: 任务ID
        """
        params = self._generate_params(API_PREPARE, file_path=file_path)
        result = self._send_request(API_PREPARE, params)
        
        if result.get('ok') == 0:
            return result.get('data')
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
        try:
            with open(file_path, 'rb') as file_obj:
                index = 1
                sig = SliceIdGenerator()
                
                while True:
                    # 读取文件分片
                    content = file_obj.read(FILE_PIECE_SIZE)
                    if not content or len(content) == 0:
                        break
                    
                    # 获取下一个分片ID
                    slice_id = sig.get_next_slice_id()
                    
                    # 构建请求参数
                    params = self._generate_params(API_UPLOAD, task_id=task_id, slice_id=slice_id)
                    
                    # 构建文件数据
                    files = {
                        'content': content
                    }
                    
                    # 发送请求
                    result = self._send_request(API_UPLOAD, params, files=files)
                    
                    if result.get('ok') != 0:
                        print(f"上传分片 {index} 失败: {result}")
                        return False
                    
                    print(f"上传分片 {index} 成功")
                    index += 1
            
            return True
        except Exception as e:
            print(f"上传文件失败: {e}")
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
        params = self._generate_params(API_MERGE, task_id=task_id, file_path=file_path)
        result = self._send_request(API_MERGE, params)
        
        return result.get('ok') == 0
    
    def get_progress(self, task_id):
        """
        获取进度接口
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 进度信息
        """
        params = self._generate_params(API_GET_PROGRESS, task_id=task_id)
        result = self._send_request(API_GET_PROGRESS, params)
        
        if result.get('ok') == 0 and result.get('data'):
            try:
                return json.loads(result.get('data'))
            except:
                return {'status': -1, 'desc': '解析进度信息失败'}
        
        return {'status': -1, 'desc': result.get('failed', '获取进度失败')}
    
    def get_result(self, task_id):
        """
        获取结果接口
        
        Args:
            task_id: 任务ID
            
        Returns:
            list: 转写结果列表
        """
        params = self._generate_params(API_GET_RESULT, task_id=task_id)
        result = self._send_request(API_GET_RESULT, params)
        
        if result.get('ok') == 0 and result.get('data'):
            try:
                return json.loads(result.get('data'))
            except:
                return []
        
        return []
    
    def upload_file(self, file_path):
        """
        上传文件并获取任务ID
        
        Args:
            file_path: 音频或视频文件路径
            
        Returns:
            str: 任务ID
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return None
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > 500 * 1024 * 1024:  # 500MB
            print("文件大小超过500MB限制")
            return None
            
        # 检查文件类型并处理
        file_ext = os.path.splitext(file_path)[1].lower()
        temp_audio_file = None
        
        # 如果是视频文件，提取音频
        if file_ext in ['.mp4', '.avi', '.mov', '.flv', '.mkv']:
            print(f"检测到视频文件: {file_path}")
            print("正在提取音频轨道...")
            try:
                # 创建临时文件
                temp_fd, temp_audio_file = tempfile.mkstemp(suffix='.mp3')
                os.close(temp_fd)
                
                # 提取音频
                video = VideoFileClip(file_path)
                video.audio.write_audiofile(temp_audio_file, codec='mp3')
                video.close()
                
                print(f"音频提取成功: {temp_audio_file}")
                file_path = temp_audio_file
            except Exception as e:
                print(f"提取音频失败: {e}")
                if temp_audio_file and os.path.exists(temp_audio_file):
                    os.remove(temp_audio_file)
                return None
        
        # 1. 预处理
        print("正在预处理...")
        task_id = self.prepare(file_path)
        if not task_id:
            print("预处理失败")
            # 如果是临时文件，删除它
            if temp_audio_file and os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            return None
        
        print(f"获取任务ID: {task_id}")
        
        # 2. 上传文件
        print("正在上传文件...")
        if not self.upload(task_id, file_path):
            print("上传文件失败")
            # 如果是临时文件，删除它
            if temp_audio_file and os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            return None
        
        # 3. 合并文件
        print("正在合并文件...")
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
    
    def format_transcript_to_text(self, transcript_data):
        """
        将转写结果格式化为完整文本
        
        Args:
            transcript_data: 转写结果数据
            
        Returns:
            str: 完整的文本文案
        """
        if not transcript_data or not isinstance(transcript_data, list):
            return ""
        
        # 按时间顺序排序片段
        sorted_segments = sorted(transcript_data, key=lambda x: int(x.get('bg', 0)))
        
        # 提取所有的 onebest 并组装
        full_text = ""
        speaker_texts = {}
        
        for segment in sorted_segments:
            onebest = segment.get('onebest', '')
            speaker = segment.get('speaker', '0')
            
            # 按说话人分组
            if speaker not in speaker_texts:
                speaker_texts[speaker] = []
            
            speaker_texts[speaker].append(onebest)
        
        # 生成完整文本，按说话人分段
        if len(speaker_texts) > 1:  # 多个说话人
            for speaker, texts in speaker_texts.items():
                speaker_text = " ".join(texts)
                full_text += f"说话人 {speaker}：{speaker_text}\n\n"
        else:  # 单个说话人
            all_texts = []
            for texts in speaker_texts.values():
                all_texts.extend(texts)
            full_text = " ".join(all_texts)
        
        return full_text.strip()
    
    def wait_for_result(self, task_id, interval=10, timeout=3600):
        """
        等待并获取转写结果
        
        Args:
            task_id: 任务ID
            interval: 轮询间隔（秒）
            timeout: 超时时间（秒）
            
        Returns:
            list: 转写结果列表
        """
        start_time = time.time()
        
        while True:
            # 检查是否超时
            if time.time() - start_time > timeout:
                print("等待结果超时")
                return None
            
            # 获取进度
            progress = self.get_progress(task_id)
            status = progress.get('status', -1)
            
            if status == 9:  # 转写完成
                print("转写完成，正在获取结果...")
                return self.get_result(task_id)
            elif status >= 0:
                desc = progress.get('desc', '处理中')
                print(f"任务状态: {desc} (状态码: {status})")
            else:
                print(f"获取进度失败: {progress}")
                return None
            
            # 等待一段时间再次查询
            time.sleep(interval)


def upload_command(args):
    """上传文件命令处理函数"""
    asr = XfyunASR(args.app_id, args.secret_key)
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


def get_result_command(args):
    """获取结果命令处理函数"""
    asr = XfyunASR(args.app_id, args.secret_key)
    
    if args.wait:
        # 等待结果
        result_data = asr.wait_for_result(args.task_id, interval=args.interval, timeout=args.timeout)
    else:
        # 直接获取结果
        progress = asr.get_progress(args.task_id)
        status = progress.get('status', -1)
        
        if status == 9:  # 转写完成
            result_data = asr.get_result(args.task_id)
        else:
            desc = progress.get('desc', '未知状态')
            result_data = None
            print(f"转写尚未完成，当前状态: {desc} (状态码: {status})")
    
    if result_data:
        result = {
            "code": 0,
            "message": "获取结果成功",
            "data": result_data
        }
        
        # 如果需要格式化为完整文本
        if args.format_text:
            full_text = asr.format_transcript_to_text(result_data)
            result["full_text"] = full_text
            
            print("\n完整文本转写结果:\n")
            print(full_text)
            
            # 如果需要保存到文件
            if args.output_file:
                try:
                    with open(args.output_file, 'w', encoding='utf-8') as f:
                        f.write(full_text)
                    print(f"\n完整文本已保存到文件: {args.output_file}")
                except Exception as e:
                    print(f"保存文件失败: {e}")
    else:
        result = {
            "code": 1,
            "message": "获取结果失败或转写尚未完成"
        }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='科大讯飞语音转写API工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 上传文件子命令
    upload_parser = subparsers.add_parser('upload', help='上传音频文件')
    upload_parser.add_argument('--app_id', required=True, help='科大讯飞应用ID')
    upload_parser.add_argument('--secret_key', required=True, help='应用密钥')
    upload_parser.add_argument('--file_path', required=True, help='音频文件路径')
    upload_parser.set_defaults(func=upload_command)
    
    # 获取结果子命令
    result_parser = subparsers.add_parser('get_result', help='获取转写结果')
    result_parser.add_argument('--app_id', required=True, help='科大讯飞应用ID')
    result_parser.add_argument('--secret_key', required=True, help='应用密钥')
    result_parser.add_argument('--task_id', required=True, help='任务ID')
    result_parser.add_argument('--wait', action='store_true', help='是否等待结果')
    result_parser.add_argument('--interval', type=int, default=10, help='轮询间隔（秒）')
    result_parser.add_argument('--timeout', type=int, default=3600, help='超时时间（秒）')
    result_parser.add_argument('--format_text', action='store_true', help='是否将结果格式化为完整文本')
    result_parser.add_argument('--output_file', help='将完整文本保存到文件')
    result_parser.set_defaults(func=get_result_command)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == '__main__':
    main()
