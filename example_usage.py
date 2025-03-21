#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科大讯飞语音转写API使用示例
"""
import argparse
import os
import time
from xfyun_asr import XfyunASR

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='科大讯飞语音转写API使用示例')
    parser.add_argument('--app_id', required=True, help='科大讯飞应用ID')
    parser.add_argument('--secret_key', required=True, help='应用密钥')
    parser.add_argument('--file_path', required=True, help='音频或视频文件路径')
    parser.add_argument('--output_file', help='输出文件路径')
    
    args = parser.parse_args()
    
    # 初始化ASR对象
    asr = XfyunASR(args.app_id, args.secret_key)
    
    # 上传文件
    print(f"正在上传文件: {args.file_path}")
    task_id = asr.upload_file(args.file_path)
    
    if not task_id:
        print("上传失败，请检查文件格式或网络连接")
        return
    
    print(f"上传成功，任务ID: {task_id}")
    print("等待转写结果...")
    
    # 等待并获取结果
    result = asr.wait_for_result(task_id)
    
    if not result:
        print("获取结果失败")
        return
    
    # 格式化为完整文本
    full_text = asr.format_transcript_to_text(result)
    
    print("\n完整转写结果:")
    print("-" * 50)
    print(full_text)
    print("-" * 50)
    
    # 保存到文件
    if args.output_file:
        try:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(full_text)
            print(f"\n转写结果已保存到文件: {args.output_file}")
        except Exception as e:
            print(f"保存文件失败: {e}")
    
    print("\n转写完成!")

if __name__ == '__main__':
    main()
