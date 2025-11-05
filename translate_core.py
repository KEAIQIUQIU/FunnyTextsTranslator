import requests
import logging
import random
import os
import re
import string

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 从LibreTranslate服务获取支持的语言列表
def get_supported_languages(base_url="http://127.0.0.1:5000"):
    try:
        response = requests.get(f"{base_url}/languages", timeout=5)
        if response.status_code == 200:
            languages = [lang['code'] for lang in response.json()]
            return languages
        else:
            logging.error(f"获取语言列表失败: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"连接LibreTranslate服务失败: {str(e)}")
        return []

# 获取支持的语言列表
COMMON_LANGUAGES = get_supported_languages()

class LibreTranslator:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def detect_language(self, text):
        """检测文本语言"""
        if not text.strip():
            return None
            
        payload = {
            "q": text
        }

        try:
            response = self.session.post(
                f"{self.base_url}/detect",
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                logging.error(f"语言检测请求失败: {response.status_code} - {response.text}")
                return None
                
            result = response.json()
            if result and len(result) > 0:
                # 返回置信度最高的语言
                return result[0]['language']
            return None
        except Exception as e:
            logging.error(f"语言检测失败: {str(e)}")
            return None

    def translate(self, text, source_lang, target_lang):
        # 起点和终点相同跳过翻译
        if source_lang == target_lang or not text.strip():
            return text

        # 清理文本
        cleaned_text = text.replace("\x00", "").strip()
        if not cleaned_text:
            return text

        payload = {
            "q": cleaned_text,
            "source": source_lang,
            "target": target_lang,
            "format": "text"
        }

        try:
            response = self.session.post(
                f"{self.base_url}/translate",
                json=payload,
                timeout=30
            )
            # 添加调试信息
            if response.status_code != 200:
                logging.error(f"翻译请求失败: {response.status_code} - {response.text}")
                return text
                
            result = response.json().get("translatedText", text)
            return result
        except Exception as e:
            logging.error(f"翻译失败: {str(e)}")
            return text

def trans(original_text, loops=40, progress_callback=None, source_lang='auto', target_lang='zh-Hans'):
    libre_translator = LibreTranslator()
    
    # 获取当前支持的语言列表
    available_languages = get_supported_languages()
    if not available_languages:
        logging.error("无法获取支持的语言列表")
        return original_text, [("错误", "无法获取支持的语言列表")]

    # 如果源语言是 'auto'，则检测语言
    if source_lang == 'auto':
        detected_lang = libre_translator.detect_language(original_text)
        if detected_lang is None:
            # 如果检测失败，使用默认语言
            detected_lang = 'en'
            logging.warning(f"语言检测失败，使用默认语言: {detected_lang}")
        source_lang = detected_lang

    # 记录所有翻译步骤
    all_steps = [("原始文本", original_text)]
    current_text = original_text
    previous_lang = source_lang

    # 检查最终目标是否为中文
    final_target_is_chinese = target_lang in ['zh', 'zh-Hans', 'zh-Hant']

    # 执行多轮翻译
    for round_idx in range(loops):
        # 检测当前文本的语言
        detected_lang = libre_translator.detect_language(current_text)
        if detected_lang is None:
            # 如果检测失败，使用上一轮的目标语言
            detected_lang = previous_lang
            logging.warning(f"语言检测失败，使用上一轮语言: {detected_lang}")

        # 确定目标语言
        if round_idx == loops - 1:
            # 最后一轮，使用指定的目标语言
            to_lang = target_lang
            
            # 检查最后一轮的目标语言是否与检测语言相同
            if detected_lang == to_lang:
                # 如果相同，选择一个新的目标语言
                other_langs = [lang for lang in available_languages if lang != detected_lang]
                if other_langs:
                    to_lang = random.choice(other_langs)
                    logging.warning(f"最后一轮检测语言和目标语言相同，已自动更改为: {to_lang}")
                else:
                    # 如果没有其他语言可用，使用英语作为默认
                    to_lang = 'en'
                    logging.warning("最后一轮检测语言和目标语言相同，且无其他语言可用，使用英语作为目标语言")
                    
        elif round_idx == loops - 2 and final_target_is_chinese:
            # 如果最终目标是中文，倒数第二轮必须是英文
            to_lang = 'en'
        else:
            # 中间轮次，绝对不允许使用中文
            # 从可用语言中排除所有中文变体
            non_chinese_langs = [lang for lang in available_languages 
                               if not lang.startswith('zh')]
            
            # 如果是中文，强制转换为英文
            if detected_lang in ['zh', 'zh-Hans', 'zh-Hant']:
                to_lang = 'en'
            else:
                # 其他语言，随机选择非当前语言且非中文的语言
                other_langs = [lang for lang in non_chinese_langs if lang != detected_lang]
                to_lang = random.choice(other_langs) if other_langs else 'en'

        # 使用LibreTranslate进行翻译
        current_text = libre_translator.translate(current_text, detected_lang, to_lang)

        all_steps.append((f"{detected_lang}→{to_lang}", current_text))
        previous_lang = to_lang  # 保存当前目标语言作为下一轮的源语言

        # 实时回调进度
        if progress_callback:
            # 构建语言路径
            lang_path = [step[0].split('→')[0] for step in all_steps[1:]]
            lang_path.append(to_lang)  # 添加最后一轮的目标语言
            
            progress_callback(
                round_idx + 1,
                loops,
                current_text,
                lang_path
            )

    return current_text, all_steps