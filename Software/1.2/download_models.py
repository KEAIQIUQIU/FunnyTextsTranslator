
import sys
import os
import gui_core
import subprocess
import time

COMMON_LANGUAGES = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'ar']

# 构建所有语言与英语的互译对
AVAILABLE_PAIRS = []
for lang in COMMON_LANGUAGES:
    if lang != 'en':
        AVAILABLE_PAIRS.append(('en', lang))
        AVAILABLE_PAIRS.append((lang, 'en'))

def download_models():
    print("正在更新包索引...")
    argostranslate.package.update_package_index()
    print("包索引更新完成！")

    print("获取可用语言包列表...")
    all_packages = argostranslate.package.get_available_packages()
    print(f"找到 {len(all_packages)} 个可用语言包")

    # 需要下载的包
    to_download = []

    # 收集需要下载的包（使用实际可用的组合）
    for from_lang, to_lang in AVAILABLE_PAIRS:
        package = next(
            (p for p in all_packages
             if p.from_code == from_lang and p.to_code == to_lang),
            None
        )
        if package:
            to_download.append(package)
        else:
            print(f'⚠️ 警告: 不存在 {from_lang} -> {to_lang} 的语言包')

    print(f"需要下载 {len(to_download)} 个语言包")

    # 下载进度跟踪
    total = len(to_download)
    downloaded = 0

    # 下载所有需要的包
    for package in to_download:
        downloaded += 1
        print(f'[{downloaded}/{total}] 下载 {package.from_code} -> {package.to_code} ...', end=' ')
        sys.stdout.flush()

        try:
            package.install()
            print("✓ 完成")
        except Exception as e:
            print(f"❌ 失败: {str(e)}")

    print('常用语言模型下载完成！')

if __name__ == "__main__":
    print("下载依赖和语言包？y/n（初次启动必须下载，后续可跳过）")
    option = input()
    if option == 'y':
        os.system("pip install -r requirements.txt")
    import argostranslate.package
    if option == 'y':
        download_models()
    print("正在启动服务...")
    subprocess.Popen('libretranslate', shell=True)
    time.sleep(5)
    gui_core.main()