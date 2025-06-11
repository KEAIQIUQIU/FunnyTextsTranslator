import time
import translators as ts
import random

# 配置参数
MAX_LENGTH = 80
LANGUAGE_LIST = ['zh', 'en', 'ar', 'ru', 'fr', 'de', 'es', 'pt', 'it', 'ja', 'ko', 'el', 'nl', 'hi', 'tr']
MAX_RETRIES = 3
FALLBACK_TRANSLATORS = ['google', 'bing']  # 备用翻译引擎
RANDOM_SEED = 42  # 随机种子
TRANSLATE_LOOPS = 40

def split_text_into_chunks(text):
    """将文本严格按字符数分割为不超过MAX_LENGTH的块"""
    return [text[i:i+MAX_LENGTH] for i in range(0, len(text), MAX_LENGTH)]

def trans(original_text):
    # 生成随机语言路径（保持起点为zh）
    random.seed(RANDOM_SEED)
    language_path = ['zh']  # 固定起点为中文
    for _ in range(TRANSLATE_LOOPS-1):  # 生成剩余TRANSLATE_LOOPS-1步
        next_lang = random.choice([l for l in LANGUAGE_LIST if l != language_path[-1]])
        language_path.append(next_lang)

    # 分块并显示数量
    original_chunks = split_text_into_chunks(original_text)
    print(f"\n📌 文本已分割为 {len(original_chunks)} 个块，每个块最大长度 {MAX_LENGTH} 字符")
    print(f"🌍 生成的语言路径：{' → '.join(language_path)}")

    # 初始化块翻译状态（存储所有轮的翻译结果）
    translated_chunks = [
        {
            "original": chunk,
            "translations": [None] * TRANSLATE_LOOPS  # 存储TRANSLATE_LOOPS轮翻译结果
        } for chunk in original_chunks
    ]

    # 进行多轮翻译
    for t in range(TRANSLATE_LOOPS):
        from_lang = language_path[t]
        to_lang = language_path[t+1] if t < TRANSLATE_LOOPS-1 else language_path[0]  # 最后一轮闭环

        print(f"\n===== 翻译轮次 {t+1} ({from_lang}→{to_lang}) =====")
        print(f"🌍 当前语言路径：{' → '.join(language_path[:t+2])}")

        # 逐块翻译
        for i in range(len(translated_chunks)):
            # 确定当前翻译的源文本：
            # 如果是第一轮，使用原文；否则使用上一轮的翻译结果
            if t == 0:
                source_text = translated_chunks[i]["original"]
            else:
                source_text = translated_chunks[i]["translations"][t-1]

                # 如果上一轮翻译失败，尝试使用更早的版本
                if source_text is None:
                    for prev_t in range(t-2, -1, -1):
                        if translated_chunks[i]["translations"][prev_t]:
                            source_text = translated_chunks[i]["translations"][prev_t]
                            break
                    if source_text is None:  # 所有历史轮次都失败
                        source_text = translated_chunks[i]["original"]

            retries = 0
            success = False

            while retries < MAX_RETRIES and not success:
                try:
                    # 尝试多个翻译引擎
                    for translator in ['alibaba'] + FALLBACK_TRANSLATORS:
                        try:
                            translated = ts.translate_text(
                                source_text,
                                from_language=from_lang,
                                to_language=to_lang,
                                translator=translator
                            )
                            if translated and translated != source_text:  # 有效翻译且非回译
                                translated_chunks[i]["translations"][t] = translated
                                success = True
                                break
                        except Exception as e:
                            continue

                    if not success:
                        raise Exception("所有翻译引擎均失败或返回无效结果")

                except Exception as e:
                    retries += 1
                    error_msg = f"块 {i+1} 翻译失败（尝试 {retries}/{MAX_RETRIES}）: {str(e)}"
                    error_msg += f" | 语言对: {from_lang}→{to_lang}"
                    error_msg += f" | 文本: {source_text[:30]}{'...' if len(source_text)>30 else ''}"

                    print(error_msg)

                    if retries < MAX_RETRIES:
                        time.sleep(0.5)

            # 终极失败处理
            if not success:
                print(f"块 {i+1} 自动翻译完全失败，需要人工干预")
                manual_input = input("请输入翻译结果（直接回车跳过）：")
                if manual_input.strip():
                    translated_chunks[i]["translations"][t] = manual_input
                else:
                    translated_chunks[i]["translations"][t] = f"[翻译失败]"

            # 显示当前块状态
            current_trans = translated_chunks[i]["translations"][t] or "未翻译"
            status = "✅" if translated_chunks[i]["translations"][t] else "❌"
            preview = current_trans[:50] + "..." if len(current_trans) > 50 else current_trans
            print(f"块 {i+1} {status}: {preview}")

        time.sleep(0.5)

    # 最终拼接输出（使用最后一轮翻译结果）
    final_output="".join(
        chunk["translations"][-1] for chunk in translated_chunks
    )

    return final_output
