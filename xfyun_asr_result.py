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
        self.task_queue = {}
    
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
            list: 转写结果文本列表
        """
        # 直接向科大讯飞API发送请求获取结果
        params = self._generate_params("getResult", task_id=task_id)
        result = self._send_request("getResult", params)
        
        if result.get("ok") and result.get("data"):
            # 提取转写结果文本
            try:
                sentences = []
                for sentence in result["data"].get("lattice", []):
                    if "json_1best" in sentence:
                        json_result = json.loads(sentence["json_1best"])
                        if "st" in json_result and "rt" in json_result["st"]:
                            for word in json_result["st"]["rt"][0]["ws"]:
                                for character in word["cw"]:
                                    sentences.append(character["w"])
                return ''.join(sentences)
            except Exception as e:
                print(f"解析转写结果失败: {str(e)}")
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


# 用于FastAPI的结果查询函数
def get_result(task_id, app_id=None, secret_key=None):
    """
    获取转写任务的状态和结果
    
    Args:
        task_id: 任务ID
        app_id: 科大讯飞应用ID（可选）
        secret_key: 应用密钥（可选）
        
    Returns:
        tuple: (status, result)
            status: 任务状态，可能是 'processing', 'completed', 'failed', 'not_found'
            result: 转写结果，如果任务未完成则为None
    """
    # 从xfyun_asr模块导入task_queue
    from xfyun_asr import task_queue
    
    # 首先，检查是否有足够的API凭证
    if not app_id or not secret_key:
        # 如果没有提供完整的API凭证，则只能从内存中查询
        task = task_queue.get(task_id)
        if not task:
            return 'not_found', None
    else:
        # 如果提供了完整的API凭证
        # 首先尝试从内存中查询
        task = task_queue.get(task_id)
        
        # 如果在内存中找不到任务，则尝试直接从科大讯飞服务器获取结果
        if not task:
            try:
                print(f"尝试直接使用科大讯飞API查询任务: {task_id}")
                result_api = XfyunASRResult(app_id, secret_key)
                # 先检查进度
                progress = result_api.get_progress(task_id)
                
                if progress is not None:
                    if progress >= 100:
                        # 如果转写完成，获取结果
                        result_data = result_api.get_result(task_id)
                        if result_data:
                            return 'completed', result_data
                        else:
                            return 'failed', "无法获取转写结果"
                    else:
                        # 如果转写未完成，返回处理中状态
                        return 'processing', f'转写进度: {progress}%'
                else:
                    return 'failed', "无法获取转写进度"
            except Exception as e:
                print(f"直接查询科大讯飞API失败: {str(e)}")
                return 'failed', str(e)
            return 'not_found', None
    
    # 检查任务状态
    if task['status'] == 'processing':
        if task['future'].done():
            try:
                # 获取科大讯飞API任务ID
                xfyun_task_id = task['future'].result()
                task['xfyun_task_id'] = xfyun_task_id
                
                # 使用任务中存储的API凭证或传入的API凭证
                used_app_id = app_id or task.get('app_id')
                used_secret_key = secret_key or task.get('secret_key')
                
                # 如果有有效的API凭证，则尝试获取结果
                if used_app_id and used_secret_key and xfyun_task_id:
                    result_api = XfyunASRResult(used_app_id, used_secret_key)
                    # 查询转写进度
                    progress = result_api.get_progress(xfyun_task_id)
                    
                    # 确保进度不是None再进行比较
                    if progress is not None and progress >= 100:
                        # 如果转写完成，获取结果
                        task['result'] = result_api.get_result(xfyun_task_id)
                        task['status'] = 'completed'
                    elif progress is None:
                        # 如果进度为None，设置为失败状态
                        task['status'] = 'failed'
                        task['result'] = '无法获取转写进度'
                    else:
                        # 如果转写未完成，保持处理中状态
                        return 'processing', f'转写进度: {progress}%'
                else:
                    # 没有有效的API凭证，无法查询结果
                    task['status'] = 'failed'
                    task['result'] = '缺少有效的API凭证或任务ID'
            except Exception as e:
                task['status'] = 'failed'
                task['result'] = str(e)
        else:
            return 'processing', None
    
    return task['status'], task['result']
