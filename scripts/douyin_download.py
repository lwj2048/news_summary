#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版抖音视频下载器
使用移动端API和更直接的方法
"""

import re
import sys
import os
import requests
import argparse
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import json

class SimpleDouyinDownloader:
    def __init__(self):
        self.session = requests.Session()
        # 使用移动端User-Agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def extract_video_id(self, url):
        """提取视频ID"""
        try:
            print(f"正在解析URL: {url}")
            
            # 处理短链接
            if 'v.douyin.com' in url:
                print("检测到短链接，正在获取重定向后的真实URL...")
                try:
                    response = self.session.get(url, allow_redirects=True, timeout=10)
                    url = response.url
                    print(f"重定向后的URL: {url}")
                except Exception as e:
                    print(f"获取重定向URL失败: {e}")
            
            # 提取视频ID
            patterns = [
                r'/video/(\d+)',
                r'item_ids=(\d+)',
                r'video/(\d+)',
                r'(\d{15,})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    video_id = match.group(1)
                    print(f"提取到视频ID: {video_id}")
                    return video_id
            
            print(f"无法从URL中提取视频ID: {url}")
            return None
            
        except Exception as e:
            print(f"提取视频ID时出错: {e}")
            return None
    
    def get_video_info(self, video_id):
        """获取视频信息"""
        try:
            print("尝试使用移动端API获取视频信息...")
            
            # 尝试移动端API
            mobile_api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={video_id}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://www.douyin.com/',
                'Origin': 'https://www.douyin.com'
            }
            
            try:
                response = self.session.get(mobile_api_url, headers=headers, timeout=15)
                print(f"移动端API响应状态码: {response.status_code}")
                
                if response.status_code == 200 and response.text.strip():
                    data = response.json()
                    print("成功获取API响应")
                    
                    if data.get('status_code') == 0 and data.get('item_list'):
                        item = data['item_list'][0]
                        
                        video_info = {
                            'title': item.get('desc', f'douyin_{video_id}'),
                            'author': item.get('author', {}).get('nickname', 'unknown'),
                            'video_url': None,
                            'cover_url': None
                        }
                        
                        # 获取视频URL
                        if item.get('video', {}).get('play_addr', {}).get('url_list'):
                            video_url = item['video']['play_addr']['url_list'][0]
                            # 替换域名获取无水印版本
                            video_url = video_url.replace('playwm', 'play')
                            video_info['video_url'] = video_url
                            print(f"成功获取视频URL: {video_url}")
                            return video_info
                
            except Exception as e:
                print(f"移动端API失败: {e}")
            
            # 如果API失败，尝试直接访问视频页面
            print("尝试直接访问视频页面...")
            return self._get_from_page(video_id)
            
        except Exception as e:
            print(f"获取视频信息时出错: {e}")
            return None
    
    def _get_from_page(self, video_id):
        """从页面获取视频信息"""
        try:
            # 尝试移动端页面
            mobile_url = f"https://m.douyin.com/share/video/{video_id}"
            print(f"尝试移动端页面: {mobile_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            response = self.session.get(mobile_url, headers=headers, timeout=15)
            print(f"移动端页面响应状态码: {response.status_code}")
            print(f"页面内容长度: {len(response.text)}")
            
            if response.status_code == 200:
                content = response.text
                
                # 查找视频URL
                video_patterns = [
                    r'"play_addr":\{"uri":"([^"]+)","url_list":\["([^"]+)"',
                    r'"playAddr":"([^"]+)"',
                    r'"downloadAddr":"([^"]+)"',
                    r'https://[^"]*\.douyinvod\.com[^"]*',
                    r'https://[^"]*\.amazonaws\.com[^"]*',
                    r'https://[^"]*\.mp4[^"]*'
                ]
                
                for pattern in video_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        for match in matches:
                            # 处理不同的匹配结果
                            if isinstance(match, tuple):
                                # 对于新的正则表达式，match是一个元组
                                if len(match) == 2:
                                    video_uri = match[0]
                                    video_url = match[1]
                                else:
                                    continue
                            else:
                                # 对于旧的正则表达式，match是一个字符串
                                video_url = match
                                video_uri = None
                            
                            if video_url.startswith('http') and ('douyinvod' in video_url or 'amazonaws' in video_url or 'mp4' in video_url or 'snssdk' in video_url):
                                print(f"找到视频URL: {video_url}")
                                
                                # 解码Unicode转义字符
                                import html
                                video_url = html.unescape(video_url)
                                # 手动替换剩余的转义字符
                                video_url = video_url.replace('\\u002F', '/')
                                print(f"解码后的URL: {video_url}")
                                
                                # 如果是带水印的URL，尝试获取无水印版本
                                if 'playwm' in video_url:
                                    video_url = video_url.replace('playwm', 'play')
                                    print(f"转换为无水印URL: {video_url}")
                                
                                video_info = {
                                    'title': f'douyin_{video_id}',
                                    'author': 'unknown',
                                    'video_url': video_url,
                                    'cover_url': None
                                }
                                
                                # 尝试获取标题
                                title_match = re.search(r'<title>(.*?)</title>', content)
                                if title_match:
                                    title = title_match.group(1)
                                    if title and title != '抖音':
                                        video_info['title'] = title
                                
                                return video_info
            
            print("移动端页面解析失败，尝试PC端页面...")
            
            # 尝试PC端页面
            pc_url = f"https://www.douyin.com/video/{video_id}"
            print(f"尝试PC端页面: {pc_url}")
            
            response = self.session.get(pc_url, headers=headers, timeout=15)
            print(f"PC端页面响应状态码: {response.status_code}")
            print(f"页面内容长度: {len(response.text)}")
            
            if response.status_code == 200:
                content = response.text
                
                # 查找JSON数据
                json_patterns = [
                    r'<script id="RENDER_DATA" type="application/json">(.*?)</script>',
                    r'window\._SSR_HYDRATED_DATA\s*=\s*({.*?})</script>'
                ]
                
                for pattern in json_patterns:
                    matches = re.findall(pattern, content, re.DOTALL)
                    if matches:
                        try:
                            json_data = matches[0]
                            import html
                            json_data = html.unescape(json_data)
                            data = json.loads(json_data)
                            
                            # 递归查找视频URL
                            video_url = self._find_video_url_in_json(data)
                            if video_url:
                                print(f"从JSON数据找到视频URL: {video_url}")
                                
                                video_info = {
                                    'title': f'douyin_{video_id}',
                                    'author': 'unknown',
                                    'video_url': video_url,
                                    'cover_url': None
                                }
                                
                                return video_info
                                
                        except Exception as e:
                            print(f"解析JSON数据失败: {e}")
                            continue
            
            print("所有方法都失败了")
            return None
            
        except Exception as e:
            print(f"从页面获取视频信息失败: {e}")
            return None
    
    def _find_video_url_in_json(self, data):
        """递归查找JSON数据中的视频URL"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['playAddr', 'downloadAddr', 'play_addr', 'download_addr', 'url']:
                    if isinstance(value, str) and value.startswith('http'):
                        if 'douyinvod' in value or 'amazonaws' in value or 'mp4' in value:
                            return value
                    elif isinstance(value, dict) and 'url_list' in value:
                        for url in value['url_list']:
                            if url.startswith('http') and ('douyinvod' in url or 'amazonaws' in url or 'mp4' in url):
                                return url
                elif isinstance(value, (dict, list)):
                    result = self._find_video_url_in_json(value)
                    if result:
                        return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_video_url_in_json(item)
                if result:
                    return result
        return None
    
    def download_video(self, video_url, filename, chunk_size=8192):
        """下载视频文件"""
        try:
            print(f"开始下载视频: {filename}")
            
            response = self.session.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 显示下载进度
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            print(f"\r下载进度: {progress:.1f}% ({downloaded_size}/{total_size} bytes)", end='', flush=True)
            
            print(f"\n下载完成: {filename}")
            return True
            
        except Exception as e:
            print(f"\n下载视频时出错: {e}")
            return False
    
    def sanitize_filename(self, filename):
        """清理文件名"""
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '_', filename)
        
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename
    
    def download_by_url(self, url, output_dir="downloads", custom_name=None):
        """根据URL下载视频"""
        print(f"正在处理URL: {url}")
        
        # 提取视频ID
        video_id = self.extract_video_id(url)
        if not video_id:
            print("无法提取视频ID，请检查URL格式")
            return False
        
        # 获取视频信息
        video_info = self.get_video_info(video_id)
        if not video_info or not video_info['video_url']:
            print("无法获取视频信息或视频URL")
            return False
        
        print(f"视频标题: {video_info['title']}")
        print(f"作者: {video_info['author']}")
        
        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        if custom_name:
            # 使用用户指定的文件名
            safe_name = self.sanitize_filename(custom_name)
            filename = f"{safe_name}.mp4"
            print(f"使用指定文件名: {filename}")
        else:
            # 使用默认的文件名格式
            safe_title = self.sanitize_filename(video_info['title'])
            filename = f"{safe_title}_{video_id}.mp4"
            print(f"使用默认文件名: {filename}")
        
        filepath = os.path.join(output_dir, filename)
        
        # 下载视频
        success = self.download_video(video_info['video_url'], filepath)
        
        if success:
            print(f"视频已保存到: {filepath}")
            return True
        else:
            print("视频下载失败")
            return False

def main():
    parser = argparse.ArgumentParser(description='简化版抖音视频下载器')
    parser.add_argument('url', nargs='?', help='抖音视频链接')
    parser.add_argument('-o', '--output', default='downloads', help='输出目录 (默认: downloads)')
    parser.add_argument('-n', '--name', help='指定下载文件名 (不包含扩展名)')
    
    args = parser.parse_args()
    
    url = args.url or os.environ.get('DOUYIN_URL')
    
    if not url:
        print("请提供抖音视频链接")
        print("使用方法:")
        print("1. 命令行参数: python douyin_simple.py 'https://v.douyin.com/xxx/'")
        print("2. 环境变量: set DOUYIN_URL='https://v.douyin.com/xxx/' && python douyin_simple.py")
        print("3. 交互式输入: python douyin_simple.py")
        print("\n可选参数:")
        print("  -o, --output DIR    指定输出目录 (默认: downloads)")
        print("  -n, --name NAME     指定下载文件名 (不包含扩展名)")
        print("\n示例:")
        print("  python douyin_simple.py '链接' -o my_videos -n 我的视频")
        
        try:
            url = input("请输入抖音视频链接: ").strip()
            if not url:
                print("未提供链接，程序退出")
                return
        except KeyboardInterrupt:
            print("\n程序被用户中断")
            return
    
    # 创建下载器实例并下载
    downloader = SimpleDouyinDownloader()
    success = downloader.download_by_url(url, args.output, args.name)
    
    if success:
        print("下载任务完成！")
    else:
        print("下载任务失败！")
        sys.exit(1)

if __name__ == "__main__":
    main() 
