import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import os
import subprocess
import requests
from translate_core import trans
from download_models import COMMON_LANGUAGES
import markdown

class TranslationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("多轮翻译工具")
        self.root.geometry("900x700")

        self.status_var = tk.StringVar(value="就绪")
        self.progress_var = tk.StringVar(value="0/0")
        self.translation_steps = []
        self.generate_report_var = tk.BooleanVar(value=False)
        self.auto_open_report_var = tk.BooleanVar(value=True)  # 新增：自动打开报告选项

        self.create_widgets()
        self.check_server_connection()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.LabelFrame(main_frame, text="输入文本（只支持英语）")
        input_frame.pack(fill=tk.X, pady=5)
        self.input_text = scrolledtext.ScrolledText(input_frame, height=8, wrap=tk.WORD)
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)

        ttk.Label(control_frame, text="循环次数:").grid(row=0, column=0, padx=5)
        self.loops_var = tk.IntVar(value=5)
        ttk.Entry(control_frame, textvariable=self.loops_var, width=5).grid(row=0, column=1)

        ttk.Button(control_frame, text="开始翻译", command=self.start_translation).grid(row=0, column=2, padx=10)

        # 修复1：将两个复选框放在同一列，并添加状态绑定
        report_frame = ttk.Frame(control_frame)
        report_frame.grid(row=0, column=3, padx=5)

        ttk.Checkbutton(report_frame, text="自动生成报告",
                        variable=self.generate_report_var,
                        command=self.update_auto_open_state).pack(side=tk.TOP, anchor=tk.W)

        # 初始状态禁用自动打开报告选项
        self.auto_open_check = ttk.Checkbutton(report_frame, text="自动打开报告",
                                               variable=self.auto_open_report_var,
                                               state=tk.DISABLED)
        self.auto_open_check.pack(side=tk.TOP, anchor=tk.W)

        self.progress = ttk.Progressbar(control_frame, orient="horizontal", length=200, mode="determinate")
        self.progress.grid(row=0, column=4, padx=10)
        ttk.Label(control_frame, textvariable=self.progress_var).grid(row=0, column=5, padx=10)

        output_frame = ttk.LabelFrame(main_frame, text="实时结果（中文）")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.output_text.config(state=tk.DISABLED)  # 初始禁用

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="手动保存报告", command=self.save_report_manual).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="清空结果", command=self.clear_results).pack(side=tk.RIGHT, padx=5)

        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=10)
        ttk.Button(status_frame, text="退出", command=self.root.quit).pack(side=tk.RIGHT, padx=10)

    def update_auto_open_state(self):
        """根据自动生成报告复选框状态更新自动打开报告选项"""
        if self.generate_report_var.get():
            self.auto_open_check.config(state=tk.NORMAL)
        else:
            self.auto_open_check.config(state=tk.DISABLED)
            self.auto_open_report_var.set(False)

    def check_server_connection(self):
        try:
            response = requests.get("http://127.0.0.1:5000", timeout=3)
            if response.status_code == 200:
                # 获取服务支持的语言
                lang_response = requests.get("http://127.0.0.1:5000/languages", timeout=3)
                if lang_response.status_code == 200:
                    lang_codes = [lang['code'] for lang in lang_response.json()]
                    # 显示实际支持的语言（与常用语言的交集）
                    supported_common = [lang for lang in COMMON_LANGUAGES if lang in lang_codes]
                    # 更新为10种语言
                    self.status_var.set(f"服务运行中 ({len(supported_common)}/10种常用语言)")
                else:
                    self.status_var.set("本地翻译服务运行中")
                return True
            else:
                raise ConnectionError()
        except:
            # 修改提示信息显示常用语言
            common_str = ",".join(COMMON_LANGUAGES)
            self.status_var.set("错误: 本地翻译服务未启动！")
            messagebox.showerror("服务异常",
                                 f"请启动LibreTranslate服务：\nlibretranslate")
            return False

    def start_translation(self):
        # 检查服务状态
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

        # 启用输出文本框
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "开始翻译...\n")
        self.output_text.config(state=tk.DISABLED)

        self.status_var.set("翻译中...")
        self.progress_var.set(f"0/{loops}")
        self.progress["value"] = 0

        threading.Thread(
            target=self.run_translation,
            args=(input_text, loops),
            daemon=True
        ).start()

    def run_translation(self, text, loops):
        try:
            def progress_callback(current, total, result, path):
                self.progress_var.set(f"{current}/{total}")
                self.progress["value"] = (current / total) * 100
                self.status_var.set(f"进度: {current}/{total}轮 当前语言: {'→'.join(path[-3:])}")

                # 更新输出文本
                self.output_text.config(state=tk.NORMAL)
                self.output_text.insert(tk.END, f"第{current}轮: {result}\n\n")
                self.output_text.see(tk.END)  # 滚动到最后
                self.output_text.config(state=tk.DISABLED)

            final_result, all_steps = trans(text, loops, progress_callback)
            self.translation_steps = all_steps

            self.output_text.config(state=tk.NORMAL)
            self.output_text.insert(tk.END, "\n✨最终结果:\n")
            self.output_text.insert(tk.END, f"{final_result}\n")
            self.output_text.config(state=tk.DISABLED)

            self.status_var.set(f"完成! 共{loops}轮翻译")

            # 自动保存报告到默认路径
            if self.generate_report_var.get():
                self.save_report_auto(final_result)

            messagebox.showinfo("完成", "翻译已完成！")

        except Exception as e:
            self.status_var.set(f"错误: {str(e)}")
            messagebox.showerror("翻译错误", str(e))

    def generate_markdown(self,final_result):
        if not self.translation_steps:
            return ""

        md_content = "# 多轮翻译报告\n\n"
        md_content += f"**原始文本**:\n```\n{self.translation_steps[0][1]}\n```\n\n"
        md_content += "## 翻译过程\n| 步骤 | 操作 | 结果 |\n|------|------|------|\n"

        for step, (action, text) in enumerate(self.translation_steps):
            # 避免文本过长影响表格显示
            display_text = text.replace("\n", "\\n")  # 处理换行符
            if len(display_text) > 100:
                display_text = display_text[:100] + "..."
            md_content += f"| {step} | {action} | {display_text} |\n"

        md_content += f"\n**最终文本**:\n```\n{final_result}\n```"
        return md_content

    def save_report_auto(self,final_result):
        """自动保存到默认路径"""
        if not self.translation_steps:
            messagebox.showwarning("无数据", "没有翻译结果可保存")
            return

        # 创建输出目录
        output_dir = os.path.join(os.getcwd(), "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 默认输出路径
        default_path = os.path.join(output_dir, "output.md")

        # 生成并保存Markdown
        md_content = self.generate_markdown(final_result)
        with open(default_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # 根据选项决定是否自动打开文件
        if self.auto_open_report_var.get():
            try:
                if os.name == 'nt':
                    os.startfile(default_path)
                elif os.name == 'posix':  # macOS/Linux
                    subprocess.call(('open', default_path))
                elif os.name == 'posix':  # 其他Unix系统
                    subprocess.call(('xdg-open', default_path))
            except Exception as e:
                messagebox.showinfo("自动保存", f"报告已保存至:\n{default_path}\n\n打开失败: {str(e)}")
        else:
            messagebox.showinfo("自动保存", f"报告已保存至:\n{default_path}")

    def save_report_manual(self,final_result):
        """手动选择保存路径"""
        if not self.translation_steps:
            messagebox.showwarning("无数据", "请先完成翻译")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown文件", "*.md")],
            initialfile="output.md"
        )
        if not file_path:
            return

        md_content = self.generate_markdown(final_result)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # 根据选项决定是否自动打开文件
        if self.auto_open_report_var.get():
            try:
                if os.name == 'nt':
                    os.startfile(file_path)
                elif os.name == 'posix':  # macOS/Linux
                    subprocess.call(('open', file_path))
                elif os.name == 'posix':  # 其他Unix系统
                    subprocess.call(('xdg-open', file_path))
            except Exception as e:
                messagebox.showinfo("手动保存", f"文件已保存至:\n{file_path}\n\n打开失败: {str(e)}")
        else:
            messagebox.showinfo("手动保存", f"文件已保存至:\n{file_path}")

    def clear_results(self):
        self.input_text.delete(1.0, tk.END)

        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)

        self.progress_var.set("0/0")
        self.progress["value"] = 0
        self.status_var.set("已重置")
        self.translation_steps = []


if __name__ == "__main__":
    root = tk.Tk()
    app = TranslationApp(root)
    root.mainloop()