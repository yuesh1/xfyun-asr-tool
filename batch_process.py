#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量处理视频/音频文件 - 基于科大讯飞语音转写API
"""
import argparse
import os
import time
import glob
import json
from concurrent.futures import ThreadPoolExecutor
from xfyun_asr import XfyunASR
from video_to_text import process_video

def find_media_files(input_dir, extensions=None):
    """
    在指定目录中查找媒体文件
    
    Args:
        input_dir: 输入目录
        extensions: 文件扩展名列表，默认为常见的音视频格式
        
    Returns:
        list: 文件路径列表
    """
    if extensions is None:
        # 默认支持的音视频格式
        extensions = [
            # 视频格式
            'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'm4v', 'webm',
            # 音频格式
            'mp3', 'wav', 'flac', 'ogg', 'm4a', 'aac', 'opus'
        ]
    
    media_files = []
    
    for ext in extensions:
        pattern = os.path.join(input_dir, f"*.{ext}")
        media_files.extend(glob.glob(pattern))
        # 检查子目录
        pattern = os.path.join(input_dir, f"**/*.{ext}")
        media_files.extend(glob.glob(pattern, recursive=True))
    
    return sorted(set(media_files))  # 去重并排序

def process_file(args):
    """处理单个文件的包装函数"""
    file_path, app_id, secret_key, output_dir, verbose = args
    
    try:
        print(f"开始处理: {os.path.basename(file_path)}")
        output_file = process_video(app_id, secret_key, file_path, output_dir, verbose)
        
        if output_file:
            print(f"完成: {os.path.basename(file_path)} -> {os.path.basename(output_file)}")
            return True, file_path, output_file
        else:
            print(f"失败: {os.path.basename(file_path)}")
            return False, file_path, None
    except Exception as e:
        print(f"处理文件时出错 {os.path.basename(file_path)}: {e}")
        return False, file_path, None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量处理视频/音频文件 - 基于科大讯飞语音转写API')
    parser.add_argument('--app_id', required=True, help='科大讯飞应用ID')
    parser.add_argument('--secret_key', required=True, help='应用密钥')
    parser.add_argument('--input_dir', required=True, help='输入目录，包含要处理的媒体文件')
    parser.add_argument('--output_dir', help='输出目录，默认为输入目录')
    parser.add_argument('--max_workers', type=int, default=1, help='最大并行处理数量，默认为1')
    parser.add_argument('--extensions', help='要处理的文件扩展名，用逗号分隔，例如: mp4,avi,mp3')
    parser.add_argument('--verbose', action='store_true', help='显示详细信息')
    
    args = parser.parse_args()
    
    # 检查输入目录是否存在
    if not os.path.isdir(args.input_dir):
        print(f"错误: 输入目录不存在: {args.input_dir}")
        return
    
    # 设置输出目录
    output_dir = args.output_dir or args.input_dir
    os.makedirs(output_dir, exist_ok=True)
    
    # 解析文件扩展名
    extensions = None
    if args.extensions:
        extensions = [ext.strip() for ext in args.extensions.split(',')]
    
    # 查找媒体文件
    media_files = find_media_files(args.input_dir, extensions)
    
    if not media_files:
        print(f"在目录 {args.input_dir} 中未找到媒体文件")
        return
    
    print(f"找到 {len(media_files)} 个媒体文件")
    
    # 创建任务列表
    tasks = [(file_path, args.app_id, args.secret_key, output_dir, args.verbose) 
             for file_path in media_files]
    
    # 处理结果统计
    results = {
        'total': len(media_files),
        'success': 0,
        'failed': 0,
        'details': []
    }
    
    # 开始计时
    start_time = time.time()
    
    # 使用线程池并行处理文件
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        for success, file_path, output_file in executor.map(process_file, tasks):
            if success:
                results['success'] += 1
                results['details'].append({
                    'file': os.path.basename(file_path),
                    'status': 'success',
                    'output': os.path.basename(output_file)
                })
            else:
                results['failed'] += 1
                results['details'].append({
                    'file': os.path.basename(file_path),
                    'status': 'failed'
                })
    
    # 计算总耗时
    elapsed_time = time.time() - start_time
    results['elapsed_time'] = f"{elapsed_time:.2f}秒"
    
    # 输出结果摘要
    print("\n处理完成!")
    print(f"总计: {results['total']} 个文件")
    print(f"成功: {results['success']} 个文件")
    print(f"失败: {results['failed']} 个文件")
    print(f"总耗时: {results['elapsed_time']}")
    
    # 保存处理报告
    report_file = os.path.join(output_dir, "batch_process_report.json")
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"处理报告已保存到: {report_file}")
    except Exception as e:
        print(f"保存处理报告失败: {e}")

if __name__ == '__main__':
    main()
