import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import os
import subprocess
import requests
import logging
import random
import re
from translate_core import trans, COMMON_LANGUAGES, LibreTranslator
import tkinter.font as tkFont

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TranslationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FunnyTextsTranslator")
        self.root.geometry("1000x800")
        
        # 设置系统默认字体
        default_font = tkFont.nametofont("TkDefaultFont")
        text_font = tkFont.nametofont("TkTextFont")
        
        # 设置图标 (如果有的话)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        self.status_var = tk.StringVar(value="就绪")
        self.progress_var = tk.StringVar(value="0/0")
        self.current_action_var = tk.StringVar(value="等待开始...")
        self.translation_steps = []
        self.generate_report_var = tk.BooleanVar(value=False)
        self.auto_open_report_var = tk.BooleanVar(value=True)

        self.create_widgets()
        self.check_server_connection()

    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 输入区域
        input_frame = ttk.LabelFrame(main_frame, text="输入文本")
        input_frame.pack(fill=tk.X, pady=5)
        
        # 语言选择框架
        lang_frame = ttk.Frame(input_frame)
        lang_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(lang_frame, text="目标语言:").pack(side=tk.LEFT, padx=5)
        self.target_lang_var = tk.StringVar(value="zh-Hans")
        self.target_lang_combo = ttk.Combobox(lang_frame, textvariable=self.target_lang_var, 
                                            values=COMMON_LANGUAGES, width=15, state="readonly")
        self.target_lang_combo.pack(side=tk.LEFT, padx=5)
        
        # 输入文本框
        self.input_text = scrolledtext.ScrolledText(input_frame, height=10, wrap=tk.WORD)
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="翻译设置")
        control_frame.pack(fill=tk.X, pady=10)
        
        # 第一行控制选项
        control_row1 = ttk.Frame(control_frame)
        control_row1.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_row1, text="循环次数:").pack(side=tk.LEFT, padx=5)
        self.loops_var = tk.IntVar(value=5)
        ttk.Spinbox(control_row1, textvariable=self.loops_var, from_=1, to=50, width=5).pack(side=tk.LEFT, padx=5)
        
        # 第二行控制选项
        control_row2 = ttk.Frame(control_frame)
        control_row2.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Checkbutton(control_row2, text="自动生成报告",
                        variable=self.generate_report_var,
                        command=self.update_auto_open_state).pack(side=tk.LEFT, padx=5)
        
        self.auto_open_check = ttk.Checkbutton(control_row2, text="自动打开报告",
                                               variable=self.auto_open_report_var,
                                               state=tk.DISABLED)
        self.auto_open_check.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_row2, text="开始翻译", command=self.start_translation).pack(side=tk.RIGHT, padx=5)

        # 进度显示区域
        progress_frame = ttk.LabelFrame(main_frame, text="进度")
        progress_frame.pack(fill=tk.X, pady=5)
        
        # 当前操作显示
        ttk.Label(progress_frame, textvariable=self.current_action_var).pack(anchor=tk.W, padx=5, pady=2)
        
        # 总进度条
        progress_bar_frame = ttk.Frame(progress_frame)
        progress_bar_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(progress_bar_frame, text="总进度:").pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(progress_bar_frame, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(progress_bar_frame, textvariable=self.progress_var).pack(side=tk.LEFT, padx=5)

        # 当前轮次结果显示区域
        self.current_result_frame = ttk.LabelFrame(main_frame, text="当前轮次结果")
        self.current_result_frame.pack(fill=tk.X, pady=5)
        
        # 创建内部框架用于显示详细信息
        inner_frame = ttk.Frame(self.current_result_frame)
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 轮次信息
        round_info_frame = ttk.Frame(inner_frame)
        round_info_frame.pack(fill=tk.X, pady=2)
        ttk.Label(round_info_frame, text="轮次:", font=("", 9, "bold")).pack(side=tk.LEFT)
        self.round_var = tk.StringVar(value="0/0")
        ttk.Label(round_info_frame, textvariable=self.round_var, font=("", 9)).pack(side=tk.LEFT, padx=5)
        
        # 语言信息
        lang_info_frame = ttk.Frame(inner_frame)
        lang_info_frame.pack(fill=tk.X, pady=2)
        ttk.Label(lang_info_frame, text="语言路径:", font=("", 9, "bold")).pack(side=tk.LEFT)
        self.lang_path_var = tk.StringVar(value="无")
        ttk.Label(lang_info_frame, textvariable=self.lang_path_var, font=("", 9)).pack(side=tk.LEFT, padx=5)
        
        # 当前翻译结果
        result_frame = ttk.Frame(inner_frame)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Label(result_frame, text="翻译结果:", font=("", 9, "bold")).pack(anchor=tk.W)
        
        self.current_result_text = scrolledtext.ScrolledText(result_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.current_result_text.pack(fill=tk.BOTH, expand=True)

        # 输出区域
        output_frame = ttk.LabelFrame(main_frame, text="日志信息")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="清空输入", command=self.clear_input).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="手动保存报告", command=self.save_report_manual).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="导出结果", command=self.export_result).pack(side=tk.RIGHT, padx=5)

        # 状态栏
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=2)
        ttk.Button(status_frame, text="退出", command=self.root.quit).pack(side=tk.RIGHT, padx=10)

    def update_auto_open_state(self):
        if self.generate_report_var.get():
            self.auto_open_check.config(state=tk.NORMAL)
        else:
            self.auto_open_check.config(state=tk.DISABLED)
            self.auto_open_report_var.set(False)

    def check_server_connection(self):
        try:
            # 尝试多个端点以提高检测可靠性
            endpoints = ["/languages", "/translate", ""]
            base_url = "http://127.0.0.1:5000"
            
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=3)
                    if response.status_code == 200:
                        # 获取服务支持的语言
                        lang_response = requests.get(f"{base_url}/languages", timeout=3)
                        if lang_response.status_code == 200:
                            supported_languages = [lang['code'] for lang in lang_response.json()]
                            
                            # 更新下拉框选项
                            self.target_lang_combo['values'] = supported_languages
                            
                            self.status_var.set(f"服务运行中 ({len(supported_languages)}种语言支持)")
                        else:
                            self.status_var.set("本地翻译服务运行中")
                        return True
                except:
                    continue  # 尝试下一个端点
            
            # 所有端点都失败
            raise ConnectionError("无法连接到LibreTranslate服务")
        
        except Exception as e:
            self.status_var.set("错误: 本地翻译服务未启动！")
            messagebox.showerror("服务异常",
                                "请启动LibreTranslate服务：\nlibretranslate")
            return False

    def start_translation(self):
        if not self.check_server_connection():
            return

        input_text = self.input_text.get("1.0", tk.END).strip()
        if not input_text:
            messagebox.showwarning("输入错误", "请输入要翻译的文本")
            return

        loops = self.loops_var.get()
        if loops < 1 or loops > 50:
            messagebox.showwarning("参数错误", "循环次数需在1-50之间")
            return

        target_lang = self.target_lang_var.get()

        # 启用输出文本框
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "开始翻译...\n")
        self.output_text.config(state=tk.DISABLED)
        
        # 清空当前结果
        self.current_result_text.config(state=tk.NORMAL)
        self.current_result_text.delete(1.0, tk.END)
        self.current_result_text.config(state=tk.DISABLED)
        self.round_var.set("0/0")
        self.lang_path_var.set("无")

        self.status_var.set("翻译中...")
        self.progress_var.set(f"0/{loops}")
        self.current_action_var.set("初始化翻译任务...")
        self.progress["value"] = 0

        # 启动翻译线程
        threading.Thread(
            target=self.run_translation,
            args=(input_text, loops, target_lang),
            daemon=True
        ).start()

    def run_translation(self, text, loops, target_lang):
        try:
            # 创建翻译器实例
            translator = LibreTranslator()
            
            # 检测源语言
            source_lang = translator.detect_language(text)
            if source_lang is None:
                # 如果检测失败，使用默认语言（英语）
                source_lang = "en"
                logging.warning("语言检测失败，使用默认语言: en")
            
            # 在run_translation方法中修改回调函数
            def progress_callback(current, total, result, path):
                self.root.after(0, lambda: self.progress_var.set(f"{current}/{total}"))
                self.root.after(0, lambda: self.progress.config(value=(current / total) * 100))
                
                # 显示完整语言路径
                path_str = " → ".join(path)
                self.root.after(0, lambda: self.current_action_var.set(f"进度: {current}/{total}轮 当前语言: {path[-1]}"))
                self.root.after(0, lambda: self.status_var.set(f"翻译中: {current}/{total}轮完成"))
                
                # 更新轮次信息
                self.root.after(0, lambda: self.round_var.set(f"{current}/{total}"))
                self.root.after(0, lambda: self.lang_path_var.set(path_str))
                
                # 更新当前结果
                self.root.after(0, self.update_current_result, f"{result}")

                # 更新输出文本
                self.root.after(0, self.update_output_text, f"\n第{current}轮完成 (路径: {path_str}):\n{result}\n{'-'*50}\n")

            # 执行翻译
            final_result, all_steps = trans(
                text, 
                loops, 
                progress_callback, 
                source_lang,  # 使用检测到的源语言
                target_lang
            )
            
            self.translation_steps = all_steps

            self.root.after(0, self.update_output_text, "\n✨ 最终结果:\n")
            self.root.after(0, self.update_output_text, f"{final_result}\n")
            
            self.root.after(0, lambda: self.status_var.set(f"完成! 共{loops}轮翻译"))
            self.root.after(0, lambda: self.current_action_var.set("翻译完成"))
            
            # 自动保存报告到默认路径
            if self.generate_report_var.get():
                self.save_report_auto(final_result)
            
            self.root.after(0, lambda: messagebox.showinfo("完成", "翻译已完成！"))
            
        except Exception as e:
            logging.error(f"翻译错误: {str(e)}")
            self.root.after(0, lambda: self.status_var.set(f"错误: {str(e)}"))
            self.root.after(0, lambda: self.current_action_var.set("翻译出错"))
            self.root.after(0, lambda: messagebox.showerror("翻译错误", f"发生错误: {str(e)}"))

    def update_output_text(self, text):
        """线程安全的输出文本更新方法"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def update_current_result(self, text):
        """更新当前轮次结果"""
        self.current_result_text.config(state=tk.NORMAL)
        self.current_result_text.delete(1.0, tk.END)
        self.current_result_text.insert(tk.END, text)
        self.current_result_text.see(tk.END)
        self.current_result_text.config(state=tk.DISABLED)

    def generate_markdown(self, final_result):
        if not self.translation_steps:
            return ""

        md_content = "# 多轮翻译报告\n\n"
        md_content += f"**原始文本**:\n```\n{self.translation_steps[0][1]}\n```\n\n"
        md_content += "## 翻译过程\n| 步骤 | 操作 | 结果 |\n|------|------|------|\n"

        for step, (action, text) in enumerate(self.translation_steps):
            display_text = text
            display_text = display_text.replace("\n", "\\n")  # 处理换行符
            md_content += f"| {step} | {action} | {display_text} |\n"

        md_content += f"\n**最终文本**:\n```\n{final_result}\n```"
        return md_content

    def save_report_auto(self, final_result):
        """自动保存到默认路径"""
        if not self.translation_steps:
            return

        # 创建输出目录
        output_dir = os.path.join(os.getcwd(), "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 生成唯一文件名
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_path = os.path.join(output_dir, f"translation_report_{timestamp}.md")

        # 生成并保存Markdown
        md_content = self.generate_markdown(final_result)
        try:
            with open(default_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            # 根据选项决定是否自动打开文件
            if self.auto_open_report_var.get():
                self.open_file(default_path)
            else:
                messagebox.showinfo("自动保存", f"报告已保存至:\n{default_path}")
        except Exception as e:
            messagebox.showerror("保存错误", f"保存报告时出错: {str(e)}")

    def save_report_manual(self):
        """手动选择保存路径"""
        if not self.translation_steps:
            messagebox.showwarning("无数据", "请先完成翻译")
            return

        # 获取最终结果
        final_result = self.translation_steps[-1][1] if self.translation_steps else ""

        file_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown文件", "*.md"), ("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile="translation_report.md"
        )
        if not file_path:
            return

        md_content = self.generate_markdown(final_result)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            # 根据选项决定是否自动打开文件
            if self.auto_open_report_var.get():
                self.open_file(file_path)
            else:
                messagebox.showinfo("手动保存", f"文件已保存至:\n{file_path}")
        except Exception as e:
            messagebox.showerror("保存错误", f"保存文件时出错: {str(e)}")

    def export_result(self):
        """导出最终结果"""
        if not self.translation_steps:
            messagebox.showwarning("无数据", "没有可导出的结果")
            return

        final_result = self.translation_steps[-1][1] if self.translation_steps else ""

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile="translation_result.txt"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_result)
            messagebox.showinfo("导出成功", f"结果已导出至:\n{file_path}")
        except Exception as e:
            messagebox.showerror("导出错误", f"导出文件时出错: {str(e)}")

    def open_file(self, file_path):
        """打开文件"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS/Linux
                subprocess.call(('open', file_path) if sys.platform == 'darwin' else ('xdg-open', file_path))
        except Exception as e:
            messagebox.showinfo("打开文件", f"文件已保存但打开失败:\n{file_path}\n\n错误: {str(e)}")

    def clear_input(self):
        """清空输入框"""
        self.input_text.delete(1.0, tk.END)

    def clear_results(self):
        """清空结果"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        self.current_result_text.config(state=tk.NORMAL)
        self.current_result_text.delete(1.0, tk.END)
        self.current_result_text.config(state=tk.DISABLED)

        self.progress_var.set("0/0")
        self.current_action_var.set("等待开始...")
        self.progress["value"] = 0
        self.status_var.set("已重置")
        self.translation_steps = []
        self.round_var.set("0/0")
        self.lang_path_var.set("无")

def main():
    root = tk.Tk()
    app = TranslationApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()