#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科大讯飞语音转写API结果查询插件
用于查询转写结果并格式化为完整文本
"""
import os
import time
import hashlib
import base64
import json
import requests

class XfyunASRResult:
    """科大讯飞语音转写API结果查询封装类"""
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
    
    def _generate_params(self, api_name, task_id=None):
        """
        根据API名称生成请求参数
        
        Args:
            api_name: API名称
            task_id: 任务ID
            
        Returns:
            dict: 请求参数字典
        """
        signature, timestamp = self._generate_signature()
        
        params = {
            "app_id": self.app_id,
            "signa": signature,
            "ts": timestamp
        }
        
        if api_name in ["getProgress", "getResult"]:
            params["task_id"] = task_id
        
        return params
    
    def _send_request(self, api_name, params):
        """
        发送HTTP请求
        
        Args:
            api_name: API名称
            params: 请求参数
            
        Returns:
            dict: 响应结果
        """
        url = f"{self.base_url}/{api_name}"
        
        try:
            response = requests.post(url, data=params, timeout=60)
            
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                return {"ok": False, "err_no": -1, "failed": f"HTTP错误: {response.status_code}"}
            
            result = response.json()
            return result
        except Exception as e:
            print(f"请求异常: {e}")
            return {"ok": False, "err_no": -1, "failed": f"请求异常: {e}"}
    
    def get_progress(self, task_id):
        """
        获取转写进度
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 进度信息
        """
        params = self._generate_params("getProgress", task_id=task_id)
        result = self._send_request("getProgress", params)
        
        if result.get("ok") and result.get("data"):
            return result["data"]
        else:
            print(f"获取进度失败: {result.get('failed', '未知错误')}")
            return None
    
    def get_result(self, task_id):
        """
        获取转写结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 转写结果
        """
        params = self._generate_params("getResult", task_id=task_id)
        result = self._send_request("getResult", params)
        
        if result.get("ok") and result.get("data"):
            return result["data"]
        else:
            print(f"获取结果失败: {result.get('failed', '未知错误')}")
            return None
    
    def wait_for_result(self, task_id, timeout=3600, interval=5):
        """
        等待并获取转写结果
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
            interval: 轮询间隔（秒）
            
        Returns:
            dict: 转写结果
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            progress = self.get_progress(task_id)
            if not progress:
                print("获取进度失败")
                time.sleep(interval)
                continue
            
            status = progress.get("status")
            if status == 9:
                print("转写完成，正在获取结果...")
                return self.get_result(task_id)
            elif status >= 0:
                progress_percent = progress.get("progress", 0)
                print(f"转写进度: {progress_percent}%，状态码: {status}")
                time.sleep(interval)
            else:
                print(f"转写失败，状态码: {status}")
                return None
        
        print(f"等待超时，已等待{timeout}秒")
        return None
    
    def format_transcript_to_text(self, result):
        """
        将转写结果格式化为完整文本
        
        Args:
            result: 转写结果
            
        Returns:
            str: 格式化后的文本
        """
        if not result or not isinstance(result, dict) or "data" not in result:
            return "转写结果为空或格式不正确"
        
        try:
            # 解析JSON数据
            data = result["data"]
            
            # 按说话人分组
            speaker_texts = {}
            
            for item in data:
                if "onebest" not in item or not item["onebest"].strip():
                    continue
                
                # 获取说话人ID，如果没有则使用默认值"0"
                speaker = item.get("speaker", "0")
                
                # 如果这个说话人还没有文本，初始化一个空列表
                if speaker not in speaker_texts:
                    speaker_texts[speaker] = []
                
                # 添加这个说话人的文本
                speaker_texts[speaker].append(item["onebest"])
            
            # 格式化输出文本
            formatted_text = ""
            
            # 如果只有一个说话人，直接输出文本
            if len(speaker_texts) == 1:
                speaker = list(speaker_texts.keys())[0]
                formatted_text = "\n".join(speaker_texts[speaker])
            else:
                # 如果有多个说话人，按说话人分段输出
                for speaker, texts in speaker_texts.items():
                    formatted_text += f"【说话人 {speaker}】\n"
                    formatted_text += "\n".join(texts)
                    formatted_text += "\n\n"
            
            return formatted_text
        except Exception as e:
            print(f"格式化文本时出错: {e}")
            return f"格式化文本时出错: {e}"


def get_result_command(args):
    """获取转写结果命令处理函数"""
    asr = XfyunASRResult(args.app_id, args.secret_key)
    
    if args.wait:
        result = asr.wait_for_result(args.task_id, args.timeout, args.interval)
    else:
        result = asr.get_result(args.task_id)
    
    if not result:
        error_result = {
            "code": 1,
            "message": "获取转写结果失败"
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        return error_result
    
    if args.format_text:
        formatted_text = asr.format_transcript_to_text({"data": result})
        
        if args.output_file:
            try:
                with open(args.output_file, 'w', encoding='utf-8') as f:
                    f.write(formatted_text)
                print(f"格式化文本已保存到: {args.output_file}")
            except Exception as e:
                print(f"保存文件时出错: {e}")
        
        success_result = {
            "code": 0,
            "message": "获取转写结果成功",
            "formatted_text": formatted_text
        }
    else:
        success_result = {
            "code": 0,
            "message": "获取转写结果成功",
            "result": result
        }
    
    print(json.dumps(success_result, ensure_ascii=False, indent=2))
    return success_result


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='科大讯飞语音转写API结果查询工具')
    parser.add_argument('--app_id', required=True, help='科大讯飞应用ID')
    parser.add_argument('--secret_key', required=True, help='应用密钥')
    parser.add_argument('--task_id', required=True, help='转写任务ID')
    parser.add_argument('--wait', action='store_true', help='是否等待转写完成')
    parser.add_argument('--timeout', type=int, default=3600, help='等待超时时间（秒）')
    parser.add_argument('--interval', type=int, default=5, help='轮询间隔（秒）')
    parser.add_argument('--format_text', action='store_true', help='是否格式化为完整文本')
    parser.add_argument('--output_file', help='输出文件路径')
    
    args = parser.parse_args()
    
    get_result_command(args)


if __name__ == '__main__':
    main()
