import string
import re
import translate_core

def remove_punctuation_and_spaces(text):
    # 移除所有标点符号（包括中英文）和空白字符
    # 使用正则表达式匹配所有非字母、非数字、非中文字符的字符
    pattern = r'[^\w\u4e00-\u9fff]'
    return re.sub(pattern, '', text)

def remove_spaces(text):
    # 创建转换表：删除所有空白字符
    translator = str.maketrans('', '', string.whitespace)
    return text.translate(translator)

original_text = ""
no_spaces_text = ""
no_punc_spaces_text = ""
trans_ans = ""

def conv():
    print("请输入文字（输入空行结束）:")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)

    global original_text
    global no_spaces_text
    global no_punc_spaces_text

    original_text = '\n'.join(lines)
    no_spaces_text = remove_spaces(original_text)
    no_punc_spaces_text = remove_punctuation_and_spaces(original_text)

def output():
    global original_text
    global no_spaces_text
    global no_punc_spaces_text
    global trans_ans

    with open("../../output.md", "w", encoding="utf-8") as file:
        file.write("# Text:\n")
        file.write("```txt\n")
        file.write(original_text + "\n")
        file.write("```\n")
        file.write("```txt\n")
        file.write(no_spaces_text + "\n")
        file.write("```\n")
        file.write("```txt\n")
        file.write(no_punc_spaces_text + "\n")
        file.write("```\n")
        file.write("# Output\n")
        file.write("```txt\n")
        file.write(trans_ans + "\n")
        file.write("```\n")

if __name__ == "__main__":
    conv()
    trans_ans= translate_core.trans(no_punc_spaces_text)
    output()
    print("结果已保存到 output.md")