import requests
import logging
import random
import os
import re
import string

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

def remove_punctuation(text):
    """移除文本中的非必要标点符号，但保留基本句子结构"""
    # 保留基本标点：句号、逗号、问号、感叹号
    text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?。，！？]', '', text)
    return text

def split_text(text, max_length=100, language='en'):
    """将文本按句子分割，对于长句子再进一步分块"""
    # 按句子分割（简单实现，可根据需要改进）
    sentences = re.split(r'([.!?。！？])', text)
    sentences = [''.join(i) for i in zip(sentences[0::2], sentences[1::2])]
    
    chunks = []
    for sentence in sentences:
        # 如果句子太长，再进一步分割
        if len(sentence) > max_length:
            if language in ['zh-Hans', 'zh-Hant']:
                # 中文按长度分割
                start = 0
                while start < len(sentence):
                    end = start + max_length
                    chunk = sentence[start:end]
                    chunks.append(chunk)
                    start = end
            else:
                # 非中文按单词分割
                words = sentence.split()
                current_chunk = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) + 1 <= max_length:
                        current_chunk.append(word)
                        current_length += len(word) + 1
                    else:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = [word]
                        current_length = len(word)
                
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
        else:
            chunks.append(sentence)
            
    return chunks

def trans(original_text, loops=40, progress_callback=None, source_lang='en', target_lang='zh-Hans', 
          chunk_size=100, chunk_progress_callback=None):
    translator = LibreTranslator()
    
    # 获取当前支持的语言列表
    available_languages = get_supported_languages()
    if not available_languages:
        logging.error("无法获取支持的语言列表")
        return original_text, [("错误", "无法获取支持的语言列表")]

    # 确保源语言和目标语言在支持的语言列表中
    if source_lang not in available_languages:
        logging.warning(f"源语言 {source_lang} 不在支持的语言列表中，使用默认值 'en'")
        source_lang = 'en'
    
    if target_lang not in available_languages:
        logging.warning(f"目标语言 {target_lang} 不在支持的语言列表中，使用默认值 'zh-Hans'")
        target_lang = 'zh-Hans'

    # 生成语言路径
    language_path = [source_lang]
    prev_lang = language_path[0]
    
    # 生成中间轮次的语言路径（排除中文）
    for i in range(loops - 1):
        # 排除当前语言和中文（中间轮次不允许中文）
        available_next_langs = [lang for lang in available_languages 
                               if lang != prev_lang and lang != 'zh-Hans' and lang != 'zh-Hant']
        
        # 如果没有可用语言，回退到所有语言（除了当前语言）
        if not available_next_langs:
            available_next_langs = [lang for lang in available_languages if lang != prev_lang]
            
        # 如果仍然没有可用语言，回退到所有语言
        if not available_next_langs:
            available_next_langs = available_languages
            
        next_lang = random.choice(available_next_langs)
        language_path.append(next_lang)
        prev_lang = next_lang
        
    # 添加目标语言到路径末尾
    language_path.append(target_lang)

    # 记录所有翻译步骤
    all_steps = [("原始文本", original_text)]
    current_text = original_text

    # 执行多轮翻译
    for round_idx in range(loops):
        from_lang = language_path[round_idx]
        to_lang = language_path[round_idx + 1]

        # 如果不是最后一轮，移除标点符号
        if round_idx < loops - 1:
            current_text = remove_punctuation(current_text)

        # 分块翻译处理
        chunks = split_text(current_text, chunk_size, from_lang)
        total_chunks = len(chunks)
        translated_chunks = []
        
        # 在每轮开始时重置块进度显示
        if chunk_progress_callback:
            chunk_progress_callback(0, total_chunks)  # 重置为0
        
        for chunk_idx, chunk in enumerate(chunks):
            # 执行翻译
            translated_chunk = translator.translate(chunk, from_lang, to_lang)
            translated_chunks.append(translated_chunk)
            
            # 调用块进度回调
            if chunk_progress_callback:
                chunk_progress_callback(chunk_idx + 1, total_chunks)
        
        # 拼接所有块的翻译结果
        current_text = "".join(translated_chunks)

        all_steps.append((f"{from_lang}→{to_lang}", current_text))

        # 实时回调进度
        if progress_callback:
            progress_callback(
                round_idx + 1,
                loops,
                current_text,
                language_path[:round_idx + 2]
            )

    return current_text, all_steps