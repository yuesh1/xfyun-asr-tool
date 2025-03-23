#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科大讯飞语音转写API V2版本实现
基于最新的讯飞语音转写API: https://www.xfyun.cn/doc/asr/ifasr_new/API.html
"""
import os
import time
import hashlib
import hmac
import base64
import json
import requests
import tempfile
import traceback
import datetime
import threading
from pathlib import Path
from typing import Dict, Tuple, Optional, Any

# 结果缓存类
class ResultCache:
    """转写结果缓存类，用于存储已完成的转写任务结果"""
    def __init__(self, max_size=100, expiration_hours=24):
        """
        初始化缓存
        
        Args:
            max_size: 缓存最大条目数
            expiration_hours: 缓存过期时间（小时）
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.expiration_hours = expiration_hours
        self.lock = threading.Lock()
    
    def get(self, order_id: str) -> Optional[Tuple[str, str]]:
        """获取缓存的结果
        
        Args:
            order_id: 订单ID
            
        Returns:
            Tuple[str, str]: (status, result) 或 None（如果缓存中不存在或已过期）
        """
        with self.lock:
            if order_id not in self.cache:
                return None
            
            cache_item = self.cache[order_id]
            # 检查是否过期
            if self._is_expired(cache_item['timestamp']):
                # 删除过期缓存
                del self.cache[order_id]
                return None
            
            return (cache_item['status'], cache_item['result'])
    
    def set(self, order_id: str, status: str, result: Optional[str]):
        """设置缓存结果
        
        Args:
            order_id: 订单ID
            status: 任务状态
            result: 转写结果
        """
        with self.lock:
            # 只缓存已完成的任务
            if status == 'completed' or status == 'failed':
                # 如果缓存已满，删除最旧的条目
                if len(self.cache) >= self.max_size:
                    self._remove_oldest()
                
                self.cache[order_id] = {
                    'status': status,
                    'result': result,
                    'timestamp': datetime.datetime.now()
                }
    
    def _is_expired(self, timestamp: datetime.datetime) -> bool:
        """检查缓存项是否已过期
        
        Args:
            timestamp: 缓存项的时间戳
            
        Returns:
            bool: 是否已过期
        """
        delta = datetime.datetime.now() - timestamp
        return delta.total_seconds() > self.expiration_hours * 3600
    
    def _remove_oldest(self):
        """删除最旧的缓存项"""
        if not self.cache:
            return
        
        # 找到最旧的条目
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
        del self.cache[oldest_key]
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()

# 创建全局缓存实例
GLOBAL_CACHE = ResultCache()

class XfyunASRV2:
    """科大讯飞语音转写API V2版本封装类"""
    def __init__(self, app_id, secret_key):
        """
        初始化
        
        Args:
            app_id: 科大讯飞开放平台应用ID
            secret_key: 应用密钥
        """
        self.app_id = app_id
        self.secret_key = secret_key
        self.base_url = "https://raasr.xfyun.cn/v2/api"
        self.cache = GLOBAL_CACHE  # 使用全局缓存
    
    def _generate_signature(self):
        """
        生成API调用签名
        
        签名生成方法：
        1. 将appId和时间戳拼接得到baseString
        2. 对baseString进行MD5哈希
        3. 使用secretKey对MD5结果进行HmacSHA1加密并Base64编码
        
        Returns:
            tuple: (signature, timestamp)
        """
        # 当前时间戳，13位
        timestamp = str(int(time.time() * 1000))
        print(f"生成签名，时间戳: {timestamp}")
        
        # 步骤1: 拼接appId和时间戳
        base_string = self.app_id + timestamp
        print(f"基础字符串: {base_string}")
        
        # 步骤2: 对baseString进行MD5哈希
        md5_result = hashlib.md5(base_string.encode('utf-8')).hexdigest()
        print(f"MD5结果: {md5_result}")
        
        # 步骤3: 使用secretKey对MD5结果进行HmacSHA1加密并Base64编码
        key = self.secret_key.encode('utf-8')
        message = md5_result.encode('utf-8')
        hmac_sha1 = hmac.new(key, message, digestmod=hashlib.sha1).digest()
        signature = base64.b64encode(hmac_sha1).decode('utf-8')
        print(f"HmacSHA1签名: {signature}")
        
        # 返回签名和时间戳
        return signature, timestamp
    
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
        
        print(f"正在请求API: {url}")
        print(f"请求参数: {params}")
        
        try:
            if files:
                print(f"上传文件大小: {len(files['file'][1]) if 'file' in files else '未知'}字节")
                # 打印文件名称
                file_name = files['file'][0] if 'file' in files else '未知'
                print(f"上传文件名称: {file_name}")
                
                # 添加请求头信息，确保请求格式正确
                headers = {
                    'Accept': 'application/json',
                }
                
                response = requests.post(url, data=params, files=files, headers=headers, timeout=180)
            else:
                response = requests.post(url, data=params, timeout=60)
            
            print(f"API响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}，响应内容: {response.text}")
                return {"code": -1, "message": f"HTTP错误: {response.status_code}, 响应: {response.text}"}
            
            try:
                result = response.json()
                print(f"API响应内容: {result}")
                
                # 检查是否有错误信息
                if "code" in result and result["code"] != 0 and result["code"] != "0":
                    error_code = result.get("code", "")
                    error_desc = result.get("descInfo", "")
                    print(f"请求返回错误码: {error_code}, 错误描述: {error_desc}")
                    
                    # 处理特定错误码
                    if error_code == "26600":
                        print("转写业务通用错误，可能是参数配置问题")
                    elif error_code == "26601":
                        print("非法应用信息，签名验证失败")
                
                return result
            except ValueError as e:
                # 如果响应不是JSON格式
                print(f"响应不是JSON格式: {response.text}")
                return {"code": -1, "message": f"响应格式错误: {e}, 原始响应: {response.text}"}
                
        except Exception as e:
            print(f"请求异常: {e}")
            return {"code": -1, "message": f"请求异常: {e}"}
    
    def upload_url(self, audio_url):
        """
        使用URL外链方式上传音频文件
        
        Args:
            audio_url: 音频文件的URL地址
            
        Returns:
            str: 订单ID (orderId)
        """
        # 生成签名
        signature, timestamp = self._generate_signature()
        
        # 从 URL 中提取文件名
        file_name = os.path.basename(audio_url)
        
        # 构建参数 - 使用URL外链方式
        params = {
            "appId": self.app_id,
            "signa": signature,
            "ts": timestamp,
            "language": "cn",
            "roleType": 1,  # 开启角色分离
            "roleNum": 2,   # 默认设置为2个说话人
            "fileName": file_name,  # 文件名
            "fileSize": 10000000,    # 使用URL外链方式时可以随机传一个数字
            "duration": 600,         # 使用URL外链方式时可以随机传一个数字
            "audioMode": "urlLink",   # 指定使用URL外链方式
            "audioUrl": audio_url     # 音频URL地址
        }
        
        print(f"完整的请求参数: {params}")
        
        # 发送请求
        result = self._send_request("upload", params)
        
        # 检查响应中是否有content字段，这是新版API的特点
        if "code" in result and result["code"] == "000000" and "content" in result and "orderId" in result["content"]:
            order_id = result["content"]["orderId"]
            print(f"上传成功，订单ID: {order_id}")
            return order_id
        # 兼容旧版格式
        elif "code" in result and (result["code"] == 0 or result["code"] == "0") and "orderId" in result:
            print(f"上传成功，订单ID: {result['orderId']}")
            return result["orderId"]
        else:
            error_msg = result.get("message", result.get("descInfo", "未知错误"))
            error_code = result.get("code", "未知错误码")
            print(f"上传失败: 错误码 {error_code}, 错误信息: {error_msg}")
            return None
    
    def upload_file(self, file_path):
        """
        上传文件接口
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            str: 订单ID (orderId)
        """
        # 生成签名
        signature, timestamp = self._generate_signature()
        
        # 检查文件是否存在和大小
        file_size = os.path.getsize(file_path)
        print(f"准备上传文件: {file_path}, 大小: {file_size} 字节")
        
        # 获取文件名
        file_name = os.path.basename(file_path)
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        
        # 估算音频时长（粗略估计，每秒约为16KB）
        duration = int(file_size / 16000)
        
        # 构建基本参数 - 添加必要的参数
        params = {
            "appId": self.app_id,
            "signa": signature,
            "ts": timestamp,
            "language": "cn",
            "roleType": 1,  # 开启角色分离
            "roleNum": 2,   # 默认设置为2个说话人
            "fileName": file_name,  # 文件名称
            "fileSize": file_size,  # 文件大小
            "duration": duration,   # 音频时长
            "audioMode": "fileStream"  # 指定使用文件流方式
        }
        
        # 打印完整的请求参数信息，便于调试
        print(f"完整的请求参数: {params}")
        
        # 准备文件
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                print(f"成功读取文件内容，大小: {len(file_content)} 字节")
                
                # 使用原始文件名
                file_name = os.path.basename(file_path)
                
                # 准备文件上传
                files = {
                    "file": (file_name, file_content, 'audio/wav')
                }
                
                # 发送请求
                result = self._send_request("upload", params, files)
                
                if "code" in result and result["code"] == 0 and "orderId" in result:
                    print(f"上传成功，订单ID: {result['orderId']}")
                    return result["orderId"]
                else:
                    error_msg = result.get("message", "未知错误")
                    error_code = result.get("code", "未知错误码")
                    print(f"上传失败: 错误码 {error_code}, 错误信息: {error_msg}")
                    return None
        except Exception as e:
            print(f"文件处理异常: {e}")
            raise Exception(f"文件处理异常: {e}")
    
    def get_result(self, order_id):
        """
        获取转写结果
        
        Args:
            order_id: 订单ID
            
        Returns:
            tuple: (status, result)
                status: 任务状态，可能是 'processing', 'completed', 'failed', 'not_found'
                result: 转写结果，如果任务未完成则为None
        """
        # 首先检查缓存
        cached_result = self.cache.get(order_id)
        if cached_result:
            print(f"从缓存中获取订单 {order_id} 的结果")
            return cached_result
        
        # 缓存中不存在，生成签名
        signature, timestamp = self._generate_signature()
        
        # 构建参数
        params = {
            "appId": self.app_id,
            "signa": signature,
            "ts": timestamp,
            "orderId": order_id
        }
        
        # 发送请求
        result = self._send_request("getResult", params)
        
        # 处理响应
        if "code" not in result:
            print(f"API响应缺少code字段: {result}")
            status, text = 'failed', None
            # 缓存失败结果
            self.cache.set(order_id, status, text)
            return status, text
        
        # 新版API返回格式处理
        if result["code"] == "000000" and "content" in result:
            # 记录成功响应
            print(f"API请求成功，响应码: {result['code']}")
            content = result["content"]
            
            # 检查订单信息
            if "orderInfo" in content:
                order_info = content["orderInfo"]
                status_code = order_info.get("status", -1)
                
                if status_code == 4:  # 转写完成
                    # 解析转写结果
                    try:
                        if "orderResult" in content and content["orderResult"]:
                            text = self._parse_result_v2(content["orderResult"])
                            # 缓存完成的结果
                            self.cache.set(order_id, 'completed', text)
                            return 'completed', text
                        else:
                            print("转写结果为空")
                            # 缓存失败结果
                            self.cache.set(order_id, 'failed', None)
                            return 'failed', None
                    except Exception as e:
                        print(f"解析结果失败: {e}")
                        # 缓存失败结果
                        self.cache.set(order_id, 'failed', None)
                        return 'failed', None
                elif status_code == 3:  # 处理中
                    est_time = content.get("taskEstimateTime", 0)
                    print(f"任务处理中，预计剩余时间: {est_time}毫秒")
                    return 'processing', None
                elif status_code == 0:  # 已创建
                    print("任务已创建，等待处理")
                    return 'processing', None
                elif status_code == 1:  # 排队中
                    print("任务排队中")
                    return 'processing', None
                elif status_code == 2:  # 上传中
                    print("音频文件上传中")
                    return 'processing', None
                elif status_code == 9:  # 转写失败
                    fail_type = order_info.get("failType", 99)
                    fail_reasons = {
                        1: "音频格式错误",
                        2: "音频内容无法识别",
                        3: "音频时长超出限制",
                        4: "音频大小超出限制",
                        5: "音频下载失败",
                        6: "音频解码失败",
                        7: "无语音内容",
                        8: "转写引擎错误",
                        9: "账户余额不足",
                        10: "转写超时",
                        11: "其他错误"
                    }
                    fail_reason = fail_reasons.get(fail_type, "未知错误")
                    print(f"任务失败，状态码: {status_code}, 失败类型: {fail_type}, 原因: {fail_reason}")
                    # 缓存失败结果
                    self.cache.set(order_id, 'failed', None)
                    return 'failed', None
                else:  # 其他状态视为失败
                    fail_type = order_info.get("failType", 99)
                    print(f"任务状态异常，状态码: {status_code}, 失败类型: {fail_type}")
                    # 缓存失败结果
                    self.cache.set(order_id, 'failed', None)
                    return 'failed', None
            else:
                print("API响应缺少orderInfo字段")
                return 'processing', None
        # 兼容旧版API返回格式
        elif result["code"] == 0:
            # 检查状态
            status = result.get("status", -1)
            
            if status == 4:  # 转写完成
                # 解析转写结果
                try:
                    text = self._parse_result(result)
                    # 缓存完成的结果
                    self.cache.set(order_id, 'completed', text)
                    return 'completed', text
                except Exception as e:
                    print(f"解析结果失败: {e}")
                    # 缓存失败结果
                    self.cache.set(order_id, 'failed', None)
                    return 'failed', None
            elif status in [0, 1, 2, 3]:  # 排队中或转写中
                status_desc = {
                    0: "已创建",
                    1: "排队中",
                    2: "上传中",
                    3: "处理中"
                }
                print(f"任务{status_desc.get(status, '处理中')}")
                return 'processing', None
            else:  # 其他状态视为失败
                print(f"任务状态异常，状态码: {status}")
                # 缓存失败结果
                self.cache.set(order_id, 'failed', None)
                return 'failed', None
        # 错误码处理
        elif result["code"] == 26602 or result["code"] == "26602":  # 任务ID不存在
            print("任务ID不存在")
            # 缓存不存在结果
            self.cache.set(order_id, 'not_found', None)
            return 'not_found', None
        elif result["code"] == 10001 or result["code"] == "10001":  # 参数错误
            error_msg = result.get("message", result.get("descInfo", "参数错误"))
            print(f"参数错误: {error_msg}")
            return 'failed', None
        elif result["code"] == 10002 or result["code"] == "10002":  # 系统错误
            error_msg = result.get("message", result.get("descInfo", "系统错误"))
            print(f"系统错误: {error_msg}")
            return 'failed', None
        elif result["code"] == 10003 or result["code"] == "10003":  # 服务忙
            print("服务忙，请稍后重试")
            return 'failed', None
        elif result["code"] == 10004 or result["code"] == "10004":  # 未授权
            print("未授权，请检查appId和密钥")
            return 'failed', None
        elif result["code"] == 10005 or result["code"] == "10005":  # 序列号无效
            print("序列号无效")
            return 'failed', None
        elif result["code"] == 10006 or result["code"] == "10006":  # 序列号已使用
            print("序列号已使用")
            return 'failed', None
        elif result["code"] == 10007 or result["code"] == "10007":  # 序列号已过期
            print("序列号已过期")
            return 'failed', None
        elif result["code"] == 10008 or result["code"] == "10008":  # 序列号类型不匹配
            print("序列号类型不匹配")
            return 'failed', None
        elif result["code"] == 10009 or result["code"] == "10009":  # 资源不存在
            print("资源不存在")
            return 'failed', None
        elif result["code"] == 10010 or result["code"] == "10010":  # 资源不可用
            print("资源不可用")
            return 'failed', None
        elif result["code"] == 10011 or result["code"] == "10011":  # 服务已过期
            print("服务已过期")
            return 'failed', None
        elif result["code"] == 10012 or result["code"] == "10012":  # 访问IP受限
            print("访问IP受限")
            return 'failed', None
        elif result["code"] == 10013 or result["code"] == "10013":  # 访问频率受限
            print("访问频率受限")
            return 'failed', None
        elif result["code"] == 10014 or result["code"] == "10014":  # 余额不足
            print("余额不足")
            return 'failed', None
        elif result["code"] == 10015 or result["code"] == "10015":  # QPS超限
            print("QPS超限")
            return 'failed', None
        else:  # 其他错误
            error_msg = result.get("message", result.get("descInfo", "未知错误"))
            print(f"API请求失败，错误码: {result['code']}, 错误信息: {error_msg}")
            # 缓存失败结果
            self.cache.set(order_id, 'failed', None)
            return 'failed', None
    
    def _parse_result_v2(self, result_str):
        """
        解析新版API返回的转写结果
        
        Args:
            result_str: API返回的结果字符串或字典
            
        Returns:
            str: 格式化后的文本
        """
        if not result_str:
            print("转写结果为空")
            return ""
        
        try:
            # 检查result_str的类型并进行相应处理
            if isinstance(result_str, str):
                try:
                    content = json.loads(result_str)
                    print("成功解析JSON字符串结果")
                except json.JSONDecodeError:
                    print(f"无法解析JSON字符串: {result_str[:100]}...")
                    # 尝试直接返回字符串，可能是纯文本结果
                    if len(result_str) > 5:  # 假设有意义的文本至少有几个字符
                        print("将字符串作为纯文本结果返回")
                        return result_str
                    return "解析结果失败"
            elif isinstance(result_str, dict):
                content = result_str
                print("使用字典类型结果")
            else:
                print(f"不支持的结果类型: {type(result_str)}")
                return "解析结果失败"
            
            # 提取文本内容
            full_text = ""
            
            # 如果是纯文本内容，直接返回
            if isinstance(content, str) and len(content) > 5:
                print("返回纯文本内容")
                return content
                
            # 如果内容是字符串并且可能是已经格式化的文本
            if "text" in content and isinstance(content["text"], str) and len(content["text"]) > 0:
                print("使用text字段的内容")
                return content["text"]
                
            # 检查是否有分段结果
            if "lattice" in content:
                print("使用lattice字段解析结果")
                for item in content["lattice"]:
                    if "json_1best" in item:
                        # 检查json_1best是字符串还是字典
                        if isinstance(item["json_1best"], str):
                            try:
                                json_result = json.loads(item["json_1best"])
                            except json.JSONDecodeError:
                                print(f"无法解析json_1best: {item['json_1best'][:50]}...")
                                continue
                        else:
                            json_result = item["json_1best"]
                            
                        if "st" in json_result and "rt" in json_result["st"]:
                            try:
                                sentence = ""
                                for word in json_result["st"]["rt"][0]["ws"]:
                                    for char in word["cw"]:
                                        sentence += char["w"]
                                full_text += sentence
                            except (KeyError, IndexError, TypeError) as e:
                                print(f"lattice解析异常: {e}")
            
            # 如果没有提取到内容，尝试使用lattice2
            if not full_text and "lattice2" in content:
                print("使用lattice2字段解析结果")
                for item in content["lattice2"]:
                    if "json_1best" in item:
                        # 检查json_1best是字符串还是字典
                        if isinstance(item["json_1best"], str):
                            try:
                                json_1best = json.loads(item["json_1best"])
                            except json.JSONDecodeError:
                                print(f"无法解析lattice2中的json_1best: {item['json_1best'][:50]}...")
                                continue
                        else:
                            json_1best = item["json_1best"]
                            
                        if "st" in json_1best:
                            try:
                                st = json_1best["st"]
                                if "rt" in st:
                                    for rt in st["rt"]:
                                        if "ws" in rt:
                                            sentence = ""
                                            for word in rt["ws"]:
                                                if "cw" in word:
                                                    for char in word["cw"]:
                                                        if "w" in char:
                                                            sentence += char["w"]
                                            full_text += sentence
                            except (KeyError, IndexError, TypeError) as e:
                                print(f"lattice2解析异常: {e}")
            
            # 尝试使用nbest字段
            if not full_text and "nbest" in content and len(content["nbest"]) > 0:
                print("使用nbest字段解析结果")
                try:
                    # 使用第一个结果
                    if isinstance(content["nbest"][0], str):
                        full_text = content["nbest"][0]
                    elif isinstance(content["nbest"][0], dict) and "sentence" in content["nbest"][0]:
                        full_text = content["nbest"][0]["sentence"]
                except (IndexError, KeyError, TypeError) as e:
                    print(f"nbest解析异常: {e}")
            
            # 尝试使用result字段
            if not full_text and "result" in content:
                print("使用result字段解析结果")
                if isinstance(content["result"], str) and len(content["result"]) > 0:
                    full_text = content["result"]
                elif isinstance(content["result"], dict) and "text" in content["result"]:
                    full_text = content["result"]["text"]
            
            # 如果仍然没有提取到内容，尝试直接使用内容
            if not full_text and isinstance(content, str) and len(content) > 5:
                print("直接使用内容作为结果")
                full_text = content
            
            # 如果仍然没有提取到内容，返回原始内容以便调试
            if not full_text:
                print(f"未能提取到文本内容，原始结果: {str(content)[:200]}...")
                return "未提取到文本内容"
            
            return full_text
        except Exception as e:
            print(f"解析结果异常: {e}, 堆栈: {traceback.format_exc()}")
            return "解析结果失败"
    
    def _parse_result(self, result):
        """
        解析转写结果
        
        Args:
            result: API返回的结果
            
        Returns:
            str: 格式化后的文本
        """
        if "content" not in result:
            return ""
        
        try:
            # 解析JSON内容
            content = json.loads(result["content"])
            
            # 提取文本内容
            full_text = ""
            
            # 检查是否有分段结果
            if "lattice" in content:
                for item in content["lattice"]:
                    if "json_1best" in item:
                        json_result = json.loads(item["json_1best"])
                        if "st" in json_result and "rt" in json_result["st"]:
                            sentence = ""
                            for word in json_result["st"]["rt"][0]["ws"]:
                                for char in word["cw"]:
                                    sentence += char["w"]
                            full_text += sentence
            
            return full_text
        except Exception as e:
            print(f"解析结果异常: {e}")
            return "解析结果失败"

def upload_audio(file_path, app_id=None, secret_key=None):
    """
    上传音频文件到讯飞服务
    
    Args:
        file_path: 音频文件路径
        app_id: 科大讯飞应用ID（可选）
        secret_key: 应用密钥（可选）
        
    Returns:
        str: 订单ID
    """
    # 如果未提供API凭证，尝试从环境变量获取
    if not app_id:
        app_id = os.environ.get('XFYUN_APP_ID')
    if not secret_key:
        secret_key = os.environ.get('XFYUN_SECRET_KEY')
    
    # 检查API凭证
    if not app_id or not secret_key:
        raise ValueError("未提供有效的API凭证，请设置XFYUN_APP_ID和XFYUN_SECRET_KEY环境变量或直接传入参数")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 检查文件类型，如果是视频文件则提取音频
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext in ['.mp4', '.avi', '.mov', '.flv', '.mkv']:
        try:
            from moviepy.editor import VideoFileClip
            print(f"检测到视频文件: {file_path}，正在提取音频...")
            
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"audio_{os.path.basename(file_path)}.wav")
            
            # 提取音频
            video = VideoFileClip(file_path)
            video.audio.write_audiofile(audio_path)
            video.close()
            
            print(f"音频提取完成: {audio_path}")
            file_path = audio_path
        except ImportError:
            raise ImportError("未安装moviepy库，无法处理视频文件。请使用pip install moviepy安装")
        except Exception as e:
            raise Exception(f"提取音频失败: {str(e)}")
    
    # 上传文件
    client = XfyunASRV2(app_id, secret_key)
    order_id = client.upload_file(file_path)
    
    if not order_id:
        raise Exception("上传文件失败")
    
    return order_id

def upload_audio_by_url(audio_url, app_id=None, secret_key=None):
    """
    使用URL外链方式上传音频文件到讯飞服务
    
    Args:
        audio_url: 音频文件的URL地址
        app_id: 科大讯飞应用ID（可选）
        secret_key: 应用密钥（可选）
        
    Returns:
        str: 订单ID
    """
    # 如果未提供API凭证，尝试从环境变量获取
    if not app_id:
        app_id = os.environ.get('XFYUN_APP_ID')
    if not secret_key:
        secret_key = os.environ.get('XFYUN_SECRET_KEY')
    
    # 检查API凭证
    if not app_id or not secret_key:
        raise ValueError("未提供有效的API凭证，请设置XFYUN_APP_ID和XFYUN_SECRET_KEY环境变量或直接传入参数")
    
    # 创建讯飞 API 对象
    asr = XfyunASRV2(app_id, secret_key)
    
    # 使用URL上传
    order_id = asr.upload_url(audio_url)
    
    return order_id

def get_transcription_result(order_id, app_id=None, secret_key=None, use_cache=True):
    """
    获取转写任务的状态和结果
    
    Args:
        order_id: 订单ID
        app_id: 科大讯飞应用ID（可选）
        secret_key: 应用密钥（可选）
        use_cache: 是否使用缓存（默认为是）
        
    Returns:
        tuple: (status, result)
            status: 任务状态，可能是 'processing', 'completed', 'failed', 'not_found'
            result: 转写结果，如果任务未完成则为None
    """
    # 如果使用缓存，先检查全局缓存
    if use_cache:
        cached_result = GLOBAL_CACHE.get(order_id)
        if cached_result:
            print(f"从全局缓存中获取订单 {order_id} 的结果")
            return cached_result
    
    # 如果未提供API凭证，尝试从环境变量获取
    if not app_id:
        app_id = os.environ.get('XFYUN_APP_ID')
    if not secret_key:
        secret_key = os.environ.get('XFYUN_SECRET_KEY')
    
    # 检查API凭证
    if not app_id or not secret_key:
        raise ValueError("未提供有效的API凭证，请设置XFYUN_APP_ID和XFYUN_SECRET_KEY环境变量或直接传入参数")
    
    # 获取结果
    client = XfyunASRV2(app_id, secret_key)
    status, result = client.get_result(order_id)
    
    # 如果使用缓存且任务已完成或失败，将结果存入全局缓存
    if use_cache and (status == 'completed' or status == 'failed' or status == 'not_found'):
        GLOBAL_CACHE.set(order_id, status, result)
    
    return status, result
