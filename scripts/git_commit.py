import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_command(command, check=True):
    """运行命令并处理错误"""
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        print(f"错误输出: {e.stderr}")
        return None

def git_status():
    """检查Git状态"""
    print("📊 检查Git状态...")
    result = run_command("git status --porcelain")
    if result and result.stdout.strip():
        print("📝 发现以下变更:")
        print(result.stdout)
        return True
    else:
        print("✅ 没有发现新的变更")
        return False

def git_add_files():
    """添加文件到Git"""
    print("📁 添加文件到Git...")
    
    # 添加news目录下的所有文件
    result = run_command("git add news/")
    if result:
        print("✅ 文件添加成功")
        return True
    else:
        print("❌ 文件添加失败")
        return False

def git_commit():
    """提交变更"""
    print("💾 提交变更...")
    
    # 获取当前时间
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    
    # 查找最新的新闻文件来生成提交信息
    news_dir = Path("news")
    if news_dir.exists():
        news_files = list(news_dir.glob("*.txt"))
        if news_files:
            latest_news = max(news_files, key=lambda x: x.stat().st_mtime)
            news_name = latest_news.stem
            
            # 检查是否有对应的总结文件
            summary_file = news_dir / f"{news_name}_summary.md"
            if summary_file.exists():
                commit_msg = f"📰 新闻更新: {news_name} - 包含原稿和AI总结"
            else:
                commit_msg = f"📰 新闻更新: {news_name}"
        else:
            commit_msg = f"📰 新闻更新: {timestamp}"
    else:
        commit_msg = f"📰 新闻更新: {timestamp}"
    
    print(f"📝 提交信息: {commit_msg}")
    
    result = run_command(f'git commit -m "{commit_msg}"')
    if result:
        print("✅ 提交成功")
        return True
    else:
        print("❌ 提交失败")
        return False

def git_push():
    """推送到远程仓库"""
    print("🚀 推送到远程仓库...")
    
    # 获取当前分支
    result = run_command("git branch --show-current")
    if result:
        current_branch = result.stdout.strip()
        print(f"🌿 当前分支: {current_branch}")
        
        push_result = run_command(f"git push origin {current_branch}")
        if push_result:
            print("✅ 推送成功")
            return True
        else:
            print("❌ 推送失败")
            return False
    else:
        print("❌ 无法获取当前分支")
        return False

def main():
    """主函数"""
    print("🚀 开始Git提交流程...")
    
    # 检查是否在Git仓库中
    if not Path(".git").exists():
        print("❌ 当前目录不是Git仓库")
        return
    
    # 检查是否有变更
    if not git_status():
        print("✨ 没有需要提交的变更")
        return
    
    # 添加文件
    if not git_add_files():
        return
    
    # 提交变更
    if not git_commit():
        return
    
    # 推送到远程
    if not git_push():
        return
    
    print("🎉 Git提交流程完成！")

if __name__ == "__main__":
    main() 