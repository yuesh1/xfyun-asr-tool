#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
视频转文字工具 - 基于科大讯飞语音转写API
"""
import argparse
import os
import time
import json
from xfyun_asr import XfyunASR

def process_video(app_id, secret_key, video_path, output_dir=None, verbose=False):
    """
    处理视频文件，提取音频并转写为文本
    
    Args:
        app_id: 科大讯飞应用ID
        secret_key: 应用密钥
        video_path: 视频文件路径
        output_dir: 输出目录，默认为视频所在目录
        verbose: 是否显示详细信息
    
    Returns:
        str: 输出文件路径
    """
    # 检查视频文件是否存在
    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在: {video_path}")
        return None
    
    # 确定输出目录和文件名
    video_dir = os.path.dirname(video_path) or '.'
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    
    if output_dir:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = video_dir
    
    output_file = os.path.join(output_dir, f"{video_name}_transcript.txt")
    
    # 初始化ASR对象
    asr = XfyunASR(app_id, secret_key)
    
    # 上传视频文件
    if verbose:
        print(f"正在处理视频: {video_path}")
        print("正在提取音频并上传...")
    
    task_id = asr.upload_file(video_path)
    
    if not task_id:
        print("上传失败，请检查视频文件格式或网络连接")
        return None
    
    if verbose:
        print(f"上传成功，任务ID: {task_id}")
        print("等待转写结果...")
    
    # 等待并获取结果
    start_time = time.time()
    result = asr.wait_for_result(task_id)
    
    if not result:
        print("获取结果失败")
        return None
    
    # 计算转写耗时
    elapsed_time = time.time() - start_time
    
    # 格式化为完整文本
    full_text = asr.format_transcript_to_text(result)
    
    # 保存到文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        if verbose:
            print(f"\n转写完成! 耗时: {elapsed_time:.2f}秒")
            print(f"转写结果已保存到文件: {output_file}")
    except Exception as e:
        print(f"保存文件失败: {e}")
        return None
    
    # 保存原始JSON结果
    json_output_file = os.path.join(output_dir, f"{video_name}_transcript.json")
    try:
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        if verbose:
            print(f"原始JSON结果已保存到文件: {json_output_file}")
    except Exception as e:
        if verbose:
            print(f"保存JSON文件失败: {e}")
    
    return output_file

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='视频转文字工具 - 基于科大讯飞语音转写API')
    parser.add_argument('--app_id', required=True, help='科大讯飞应用ID')
    parser.add_argument('--secret_key', required=True, help='应用密钥')
    parser.add_argument('--video_path', required=True, help='视频文件路径')
    parser.add_argument('--output_dir', help='输出目录，默认为视频所在目录')
    parser.add_argument('--verbose', action='store_true', help='显示详细信息')
    
    args = parser.parse_args()
    
    output_file = process_video(
        args.app_id,
        args.secret_key,
        args.video_path,
        args.output_dir,
        args.verbose
    )
    
    if output_file:
        print(f"视频转写完成，结果保存在: {output_file}")
    else:
        print("视频转写失败")

if __name__ == '__main__':
    main()
