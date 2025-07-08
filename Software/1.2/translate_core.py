import requests
import logging
import random

from download_models import COMMON_LANGUAGES

class LibreTranslator:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

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
            result = response.json().get("translatedText", text)
            return result
        except Exception as e:
            logging.error(f"翻译失败: {str(e)}")
            return text


def trans(original_text, loops=40, progress_callback=None):
    translator = LibreTranslator()

    # 生成语言路径
    language_path = ['en']
    prev_lang = language_path[0]
    for _ in range(loops - 1):
        available_langs = [lang for lang in COMMON_LANGUAGES if lang != prev_lang]
        next_lang = random.choice(available_langs)
        language_path.append(next_lang)
        prev_lang = next_lang
    language_path.append('zh')

    # 记录所有翻译步骤
    all_steps = [("原始文本", original_text)]
    current_text = original_text

    # 执行多轮翻译
    for round_idx in range(loops):
        from_lang = language_path[round_idx]
        to_lang = language_path[round_idx + 1]

        # 记录翻译前的文本
        all_steps.append((f"{from_lang}→{to_lang}", current_text))

        # 执行翻译
        current_text = translator.translate(current_text, from_lang, to_lang)

        # 实时回调进度
        if progress_callback:
            progress_callback(
                round_idx + 1,
                loops,
                current_text,
                language_path[:round_idx + 2]
            )

    return current_text, all_steps


# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='translation.log',
    filemode='a'
)