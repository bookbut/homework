import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import threading
import time
from datetime import datetime
import shutil
import subprocess
import platform
import hashlib
import difflib
import re
from pypinyin import pinyin, Style  # 用于中文拼音排序


class HomeworkCheckSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("学生作业检查系统 - 多班级版 - 雷州市职业高级中学 林勇良")
        self.root.geometry("1500x800")

        # 设置窗口图标和作者信息
        self.setup_window_info()

        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TButton", padding=4, relief="flat", background="#4CAF50", foreground="black")
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Arial", 9))
        self.style.configure("Header.TLabel", background="#f0f0f0", font=("Arial", 10, "bold"))
        self.style.configure("Author.TLabel", background="#e3f2fd", font=("Arial", 8), foreground="#1565C0")

        # 初始化数据
        self.current_class = "默认班级"
        self.classes = {}
        self.file_extensions = [".py", ".txt", ".doc", ".docx", ".pdf", ".java", ".cpp"]
        self.check_mode = "folder"
        self.auto_refresh = False
        self.refresh_interval = 10
        self.similarity_threshold = 95  # 默认阈值设为95%

        # 排序相关变量
        self.sort_column = "状态"
        self.sort_reverse = False

        # 控件变量
        self.dir_var = tk.StringVar()
        self.mode_var = tk.StringVar(value=self.check_mode)
        self.refresh_var = tk.BooleanVar(value=self.auto_refresh)
        self.interval_var = tk.StringVar(value=str(self.refresh_interval))
        self.class_var = tk.StringVar(value=self.current_class)
        self.similarity_var = tk.StringVar(value=str(self.similarity_threshold))

        # 线程控制
        self.refresh_thread = None
        self.stop_refresh = False
        self.is_checking = False

        # 加载配置并创建界面
        self.load_all_classes()
        self.create_widgets()
        self.start_auto_refresh()

    def setup_window_info(self):
        """设置窗口作者信息"""
        # 创建底部状态栏显示作者信息
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        author_info = "学校：雷州市职业高级中学 | 作者：林勇良"
        self.author_label = ttk.Label(self.status_frame, text=author_info, style="Author.TLabel")
        self.author_label.pack(side=tk.RIGHT, padx=5, pady=2)

    def create_widgets(self):
        # 创建主分割面板
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧操作面板
        left_frame = ttk.Frame(main_paned, width=450)
        main_paned.add(left_frame, weight=1)

        # 右侧结果面板
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        # 创建界面组件
        self.create_left_panel(left_frame)
        self.create_right_panel(right_frame)

        # 加载当前班级数据
        self.load_current_class_data()

    def create_left_panel(self, parent):
        # 班级管理部分
        class_frame = ttk.LabelFrame(parent, text="班级管理", padding="5")
        class_frame.pack(fill=tk.X, pady=3, padx=3)

        class_top_frame = ttk.Frame(class_frame)
        class_top_frame.pack(fill=tk.X, pady=2)

        ttk.Label(class_top_frame, text="当前班级:").pack(side=tk.LEFT)
        self.class_combo = ttk.Combobox(class_top_frame, textvariable=self.class_var,
                                        values=list(self.classes.keys()), width=18)
        self.class_combo.pack(side=tk.LEFT, padx=3)
        self.class_combo.bind('<<ComboboxSelected>>', self.on_class_changed)

        ttk.Button(class_top_frame, text="新建班级", command=self.create_new_class).pack(side=tk.LEFT, padx=3)
        ttk.Button(class_top_frame, text="删除班级", command=self.delete_class).pack(side=tk.LEFT, padx=3)

        class_bottom_frame = ttk.Frame(class_frame)
        class_bottom_frame.pack(fill=tk.X, pady=2)

        ttk.Button(class_bottom_frame, text="保存配置", command=self.save_current_class).pack(side=tk.LEFT, padx=3)
        ttk.Button(class_bottom_frame, text="导出配置", command=self.export_class_config).pack(side=tk.LEFT, padx=3)
        ttk.Button(class_bottom_frame, text="导入配置", command=self.import_class_config).pack(side=tk.LEFT, padx=3)

        # 学生名单部分
        student_frame = ttk.LabelFrame(parent, text="学生名单", padding="5")
        student_frame.pack(fill=tk.BOTH, expand=True, pady=3, padx=3)

        ttk.Label(student_frame, text="学生名单（每行一个名字，支持学号+姓名格式）:").pack(anchor=tk.W)

        self.student_text = tk.Text(student_frame, height=8, width=50)
        self.student_text.pack(fill=tk.BOTH, expand=True, pady=3)

        button_frame = ttk.Frame(student_frame)
        button_frame.pack(fill=tk.X, pady=2)

        ttk.Button(button_frame, text="保存名单", command=self.save_students).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="清空名单", command=self.clear_students).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="导入名单", command=self.import_students_from_file).pack(side=tk.LEFT, padx=3)

        # 设置部分
        settings_frame = ttk.LabelFrame(parent, text="系统设置", padding="5")
        settings_frame.pack(fill=tk.X, pady=3, padx=3)

        # 根目录选择
        dir_frame = ttk.Frame(settings_frame)
        dir_frame.pack(fill=tk.X, pady=2)

        ttk.Label(dir_frame, text="作业根目录:").pack(side=tk.LEFT)
        ttk.Entry(dir_frame, textvariable=self.dir_var, width=35).pack(side=tk.LEFT, padx=3)
        ttk.Button(dir_frame, text="浏览", command=self.browse_directory).pack(side=tk.LEFT, padx=3)

        # 检查模式选择
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill=tk.X, pady=2)

        ttk.Label(mode_frame, text="检查模式:").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="文件夹模式", variable=self.mode_var,
                        value="folder", command=self.update_mode).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="文件模式", variable=self.mode_var,
                        value="file", command=self.update_mode).pack(side=tk.LEFT, padx=5)

        # 文件扩展名设置
        ext_frame = ttk.Frame(settings_frame)
        ext_frame.pack(fill=tk.X, pady=2)

        ttk.Label(ext_frame, text="文件扩展名:").pack(side=tk.LEFT)

        self.ext_frame_inner = ttk.Frame(ext_frame)
        self.ext_frame_inner.pack(side=tk.LEFT, padx=3)

        self.update_extensions()

        ttk.Button(ext_frame, text="添加", command=self.add_extension).pack(side=tk.LEFT, padx=3)

        # 自动刷新设置
        refresh_frame = ttk.Frame(settings_frame)
        refresh_frame.pack(fill=tk.X, pady=2)

        ttk.Label(refresh_frame, text="自动刷新:").pack(side=tk.LEFT)
        ttk.Checkbutton(refresh_frame, text="启用", variable=self.refresh_var,
                        command=self.toggle_auto_refresh).pack(side=tk.LEFT, padx=5)

        ttk.Label(refresh_frame, text="间隔(秒):").pack(side=tk.LEFT, padx=(10, 2))
        self.interval_spinbox = tk.Spinbox(refresh_frame, from_=5, to=300, width=5, textvariable=self.interval_var,
                                           command=self.update_refresh_interval)
        self.interval_spinbox.pack(side=tk.LEFT, padx=3)

        # 抄袭检测设置
        plagiarism_frame = ttk.Frame(settings_frame)
        plagiarism_frame.pack(fill=tk.X, pady=2)

        ttk.Label(plagiarism_frame, text="抄袭检测:").pack(side=tk.LEFT)
        ttk.Checkbutton(plagiarism_frame, text="启用", variable=tk.BooleanVar(value=True),
                        state="disabled").pack(side=tk.LEFT, padx=5)

        ttk.Label(plagiarism_frame, text="相似度阈值(%):").pack(side=tk.LEFT, padx=(10, 2))
        self.similarity_spinbox = tk.Spinbox(plagiarism_frame, from_=50, to=100, width=5,
                                             textvariable=self.similarity_var,
                                             command=self.update_similarity_threshold)
        self.similarity_spinbox.pack(side=tk.LEFT, padx=3)

        # 添加绑定事件，确保实时更新阈值
        self.similarity_spinbox.bind('<Return>', lambda e: self.update_similarity_threshold())
        self.similarity_spinbox.bind('<FocusOut>', lambda e: self.update_similarity_threshold())

        # 操作按钮区域
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=5, padx=3)

        # 统计信息标签
        self.stats_label = ttk.Label(action_frame, text="", font=("Arial", 9, "bold"))
        self.stats_label.pack(side=tk.LEFT, padx=3)

        # 最后检查时间标签
        self.time_label = ttk.Label(action_frame, text="", font=("Arial", 8), foreground="gray")
        self.time_label.pack(side=tk.LEFT, padx=10)

        ttk.Button(action_frame, text="立即检查", command=self.check_homework).pack(side=tk.RIGHT, padx=3)
        ttk.Button(action_frame, text="作业迁移", command=self.migrate_homework).pack(side=tk.RIGHT, padx=3)

    def create_right_panel(self, parent):
        # 结果显示
        result_frame = ttk.LabelFrame(parent, text="检查结果", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=3, padx=3)

        # 创建树形视图
        columns = ("学生", "状态", "相似度", "详细信息", "最后更新时间")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=25)

        # 设置列标题和绑定点击事件
        for col in columns:
            self.result_tree.heading(col, text=col, command=lambda c=col: self.treeview_sort_column(c))
            if col == "最后更新时间":
                self.result_tree.column(col, width=120)
            elif col == "学生":
                self.result_tree.column(col, width=100)
            elif col == "状态":
                self.result_tree.column(col, width=80)
            elif col == "相似度":
                self.result_tree.column(col, width=60)
            else:
                self.result_tree.column(col, width=300)

        # 定义标签样式
        self.result_tree.tag_configure('submitted', background='#e8f5e9')
        self.result_tree.tag_configure('not_submitted', background='#f5f5f5')
        self.result_tree.tag_configure('suspected_plagiarism', background='#ffebee')

        # 绑定双击事件
        self.result_tree.bind("<Double-1>", self.on_item_double_click)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)

        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def get_chinese_pinyin(self, text):
        """获取中文字符串的拼音，用于排序"""
        try:
            # 将中文转换为拼音首字母
            pinyin_list = pinyin(text, style=Style.FIRST_LETTER)
            return ''.join([item[0] for item in pinyin_list]).lower()
        except:
            # 如果转换失败，返回原文本
            return text.lower()

    def treeview_sort_column(self, col):
        """对树形视图的列进行排序 - 优化：支持中文拼音排序和状态二级排序"""
        items = [(self.result_tree.set(item, col), item) for item in self.result_tree.get_children('')]

        if col == "状态":
            # 状态排序：先按状态，再按相似度二级排序
            status_order = {"已提交": 1, "疑似抄袭": 2, "未提交": 3}

            def get_sort_key(item):
                status = self.result_tree.set(item[1], "状态")
                similarity_str = self.result_tree.set(item[1], "相似度")

                # 获取相似度数值
                try:
                    similarity_value = float(similarity_str.strip('%'))
                except (ValueError, AttributeError):
                    similarity_value = 0.0

                # 状态优先级 + 相似度（降序）
                status_rank = status_order.get(status, 4)
                return (status_rank, -similarity_value)  # 相似度降序

            items.sort(key=get_sort_key, reverse=self.sort_reverse)

        elif col == "学生":
            # 学生姓名按拼音排序
            def get_name_key(item):
                name = item[0]
                # 尝试提取拼音
                pinyin_key = self.get_chinese_pinyin(name)
                return pinyin_key

            items.sort(key=get_name_key, reverse=self.sort_reverse)

        elif col == "相似度":
            # 相似度列按数值排序
            def get_similarity_value(s):
                try:
                    return float(s.strip('%'))
                except (ValueError, AttributeError):
                    return 0.0

            items.sort(key=lambda x: get_similarity_value(x[0]), reverse=self.sort_reverse)

        else:
            # 其他列按字母顺序排序
            items.sort(key=lambda x: x[0].lower(), reverse=self.sort_reverse)

        # 重新排列项
        for index, (_, item) in enumerate(items):
            self.result_tree.move(item, '', index)

        # 切换排序方向
        self.sort_reverse = not self.sort_reverse

    def on_item_double_click(self, event):
        """双击结果项时打开学生作业目录"""
        selection = self.result_tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.result_tree.item(item, "values")
        if not values:
            return

        student_name = values[0]
        status = values[1]

        if status in ["已提交", "疑似抄袭"]:
            root_dir = self.dir_var.get()
            if not root_dir or not os.path.exists(root_dir):
                messagebox.showerror("错误", "作业根目录不存在")
                return

            if self.check_mode == "folder":
                student_dir = os.path.join(root_dir, student_name)
                if os.path.exists(student_dir) and os.path.isdir(student_dir):
                    self.open_file_explorer(student_dir)
                else:
                    messagebox.showinfo("提示", f"找不到学生 '{student_name}' 的文件夹")
            else:
                self.open_file_explorer(root_dir)
        else:
            root_dir = self.dir_var.get()
            if root_dir and os.path.exists(root_dir):
                self.open_file_explorer(root_dir)
            else:
                messagebox.showerror("错误", "作业根目录不存在")

    def open_file_explorer(self, path):
        """打开文件资源管理器并定位到指定路径"""
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开目录: {str(e)}")

    def calculate_md5(self, file_path):
        """计算文件的MD5哈希值"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
            return file_hash.hexdigest()
        except Exception as e:
            print(f"计算MD5时出错: {e}")
            return None

    def calculate_similarity(self, file1_path, file2_path):
        """计算两个文件的内容相似度"""
        try:
            # 根据文件扩展名决定读取方式
            ext1 = os.path.splitext(file1_path)[1].lower()
            ext2 = os.path.splitext(file2_path)[1].lower()

            # 文本文件使用文本模式读取
            text_extensions = ['.py', '.txt', '.java', '.cpp', '.c', '.h', '.js', '.html', '.css']

            if ext1 in text_extensions and ext2 in text_extensions:
                with open(file1_path, 'r', encoding='utf-8', errors='ignore') as f1:
                    content1 = f1.read()

                with open(file2_path, 'r', encoding='utf-8', errors='ignore') as f2:
                    content2 = f2.read()

                # 使用difflib计算相似度
                similarity = difflib.SequenceMatcher(None, content1, content2).ratio()
                return round(similarity * 100, 2)
            else:
                # 对于非文本文件，比较文件大小作为简单相似度
                size1 = os.path.getsize(file1_path)
                size2 = os.path.getsize(file2_path)
                if size1 == 0 and size2 == 0:
                    return 100.0
                elif size1 == 0 or size2 == 0:
                    return 0.0
                else:
                    size_ratio = min(size1, size2) / max(size1, size2)
                    return round(size_ratio * 100, 2)
        except Exception as e:
            print(f"计算相似度时出错: {e}")
            return 0

    def get_file_modification_time(self, file_path):
        """获取文件的最后修改时间"""
        try:
            if os.path.exists(file_path):
                timestamp = os.path.getmtime(file_path)
                return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"获取文件修改时间时出错: {e}")
        return "未知"

    def extract_student_name(self, text):
        """从字符串中提取学生姓名，支持多种格式"""
        students = self.classes[self.current_class]["students"]

        # 首先尝试精确匹配
        for student in students:
            if student in text:
                return student

        # 如果精确匹配失败，尝试模糊匹配
        for student in students:
            patterns = [
                rf'.*{re.escape(student)}.*',
                rf'.*\d+[\-\_\s]*{re.escape(student)}.*',
                rf'.*{re.escape(student)}[\-\_\s]*\d+.*',
            ]

            for pattern in patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    return student

        return None

    def find_student_folder(self, root_dir, student):
        """在根目录中查找学生文件夹，支持模糊匹配"""
        if not os.path.exists(root_dir):
            return None

        for item in os.listdir(root_dir):
            item_path = os.path.join(root_dir, item)
            if os.path.isdir(item_path):
                extracted_name = self.extract_student_name(item)
                if extracted_name == student:
                    return item_path
        return None

    def find_student_files(self, root_dir, student):
        """在根目录中查找学生文件，支持模糊匹配"""
        found_files = []
        if not os.path.exists(root_dir):
            return found_files

        for file in os.listdir(root_dir):
            file_path = os.path.join(root_dir, file)
            if os.path.isfile(file_path):
                extracted_name = self.extract_student_name(file)
                if extracted_name == student:
                    if any(file.lower().endswith(ext.lower()) for ext in self.file_extensions):
                        found_files.append((file, file_path))
        return found_files

    def check_plagiarism(self, student_files):
        """检查学生作业之间的抄袭情况"""
        plagiarism_results = {}

        # 收集所有文件的MD5和路径
        file_hashes = {}
        for student, file_path in student_files.items():
            md5_hash = self.calculate_md5(file_path)
            if md5_hash:
                if md5_hash not in file_hashes:
                    file_hashes[md5_hash] = []
                file_hashes[md5_hash].append((student, file_path))

        # 检查MD5相同的文件（完全相同的文件）
        for md5_hash, files in file_hashes.items():
            if len(files) > 1:
                for student, file_path in files:
                    other_students = [s for s, _ in files if s != student]
                    plagiarism_results[student] = {
                        'type': 'identical',
                        'similarity': 100,
                        'other_students': other_students,
                        'md5_hash': md5_hash
                    }

        # 检查内容相似度高的文件 - 使用当前阈值
        students = list(student_files.keys())
        for i in range(len(students)):
            for j in range(i + 1, len(students)):
                student1 = students[i]
                student2 = students[j]

                # 如果已经检测到完全相同的文件，跳过
                if student1 in plagiarism_results and plagiarism_results[student1]['type'] == 'identical':
                    continue
                if student2 in plagiarism_results and plagiarism_results[student2]['type'] == 'identical':
                    continue

                similarity = self.calculate_similarity(
                    student_files[student1],
                    student_files[student2]
                )

                # 使用当前阈值判定抄袭
                if similarity >= self.similarity_threshold:
                    # 更新学生1的结果
                    if student1 not in plagiarism_results:
                        plagiarism_results[student1] = {
                            'type': 'similar',
                            'similarity': similarity,
                            'other_students': [student2]
                        }
                    else:
                        if student2 not in plagiarism_results[student1]['other_students']:
                            plagiarism_results[student1]['other_students'].append(student2)
                        if similarity > plagiarism_results[student1]['similarity']:
                            plagiarism_results[student1]['similarity'] = similarity

                    # 更新学生2的结果
                    if student2 not in plagiarism_results:
                        plagiarism_results[student2] = {
                            'type': 'similar',
                            'similarity': similarity,
                            'other_students': [student1]
                        }
                    else:
                        if student1 not in plagiarism_results[student2]['other_students']:
                            plagiarism_results[student2]['other_students'].append(student1)
                        if similarity > plagiarism_results[student2]['similarity']:
                            plagiarism_results[student2]['similarity'] = similarity

        return plagiarism_results

    def update_similarity_threshold(self):
        """更新相似度阈值"""
        try:
            new_threshold = int(self.similarity_var.get())
            if 50 <= new_threshold <= 100:
                self.similarity_threshold = new_threshold
                # 立即保存到当前班级配置
                if self.current_class in self.classes:
                    self.classes[self.current_class]["similarity_threshold"] = new_threshold
            else:
                self.similarity_threshold = 95
                self.similarity_var.set("95")
                if self.current_class in self.classes:
                    self.classes[self.current_class]["similarity_threshold"] = 95
        except ValueError:
            self.similarity_threshold = 95
            self.similarity_var.set("95")
            if self.current_class in self.classes:
                self.classes[self.current_class]["similarity_threshold"] = 95

    def load_all_classes(self):
        """加载所有班级配置 - 优化：加载上一次的班级"""
        try:
            if os.path.exists("class_configs.json"):
                with open("class_configs.json", "r", encoding="utf-8") as f:
                    self.classes = json.load(f)

                # 尝试加载上一次的当前班级
                if "last_current_class" in self.classes and self.classes["last_current_class"] in self.classes:
                    self.current_class = self.classes["last_current_class"]
                    self.class_var.set(self.current_class)
            else:
                self.classes = {}

            # 如果没有默认班级，创建一个
            if "默认班级" not in self.classes:
                self.classes["默认班级"] = self.get_default_class_config()

        except Exception as e:
            print(f"加载班级配置时出错: {str(e)}")
            self.classes = {"默认班级": self.get_default_class_config()}

    def get_default_class_config(self):
        """获取默认班级配置"""
        return {
            "students": [],
            "root_directory": "",
            "file_extensions": [".py", ".txt", ".doc", ".docx", ".pdf", ".java", ".cpp"],
            "check_mode": "folder",
            "auto_refresh": False,
            "refresh_interval": 10,
            "similarity_threshold": 95
        }

    def save_all_classes(self):
        """保存所有班级配置 - 优化：保存当前班级信息"""
        try:
            # 保存当前班级信息
            self.classes["last_current_class"] = self.current_class

            with open("class_configs.json", "w", encoding="utf-8") as f:
                json.dump(self.classes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"保存班级配置时出错: {str(e)}")

    def load_current_class_data(self):
        """加载当前班级数据到界面"""
        if self.current_class in self.classes:
            config = self.classes[self.current_class]

            # 更新界面控件
            self.student_text.delete(1.0, tk.END)
            if config["students"]:
                self.student_text.insert(tk.END, "\n".join(config["students"]))

            self.dir_var.set(config.get("root_directory", ""))
            self.file_extensions = config.get("file_extensions",
                                              [".py", ".txt", ".doc", ".docx", ".pdf", ".java", ".cpp"])
            self.check_mode = config.get("check_mode", "folder")
            self.auto_refresh = config.get("auto_refresh", False)
            self.refresh_interval = config.get("refresh_interval", 10)

            # 确保正确加载相似度阈值
            self.similarity_threshold = config.get("similarity_threshold", 95)
            self.similarity_var.set(str(self.similarity_threshold))

            # 更新界面显示
            self.update_extensions()
            self.mode_var.set(self.check_mode)
            self.refresh_var.set(self.auto_refresh)
            self.interval_var.set(str(self.refresh_interval))

    def save_current_class(self):
        """保存当前班级配置"""
        # 先保存学生名单
        self.save_students()

        if self.current_class in self.classes:
            # 确保获取最新的阈值设置
            self.update_similarity_threshold()

            self.classes[self.current_class].update({
                "root_directory": self.dir_var.get(),
                "file_extensions": self.file_extensions,
                "check_mode": self.check_mode,
                "auto_refresh": self.auto_refresh,
                "refresh_interval": self.refresh_interval,
                "similarity_threshold": self.similarity_threshold
            })
            self.save_all_classes()
            messagebox.showinfo("成功", "班级配置已保存")

    def on_class_changed(self, event=None):
        """切换班级时的处理"""
        new_class = self.class_var.get()
        if new_class != self.current_class and new_class in self.classes:
            self.save_current_class()
            self.current_class = new_class
            self.load_current_class_data()
            self.clear_results()

    def create_new_class(self):
        """创建新班级"""

        def save_new_class():
            class_name = name_entry.get().strip()
            if not class_name:
                messagebox.showerror("错误", "班级名称不能为空")
                return

            if class_name in self.classes:
                messagebox.showerror("错误", "班级名称已存在")
                return

            self.classes[class_name] = self.get_default_class_config()
            self.save_all_classes()

            self.class_combo['values'] = list(self.classes.keys())
            self.class_var.set(class_name)
            self.on_class_changed()

            new_class_dialog.destroy()

        new_class_dialog = tk.Toplevel(self.root)
        new_class_dialog.title("新建班级")
        new_class_dialog.geometry("300x120")
        new_class_dialog.resizable(False, False)

        ttk.Label(new_class_dialog, text="请输入班级名称:").pack(pady=10)
        name_entry = ttk.Entry(new_class_dialog, width=20)
        name_entry.pack(pady=5)
        name_entry.focus()

        button_frame = ttk.Frame(new_class_dialog)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="确定", command=save_new_class).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=new_class_dialog.destroy).pack(side=tk.LEFT, padx=10)

        new_class_dialog.transient(self.root)
        new_class_dialog.grab_set()
        self.root.wait_window(new_class_dialog)

    def delete_class(self):
        """删除当前班级"""
        if self.current_class == "默认班级":
            messagebox.showerror("错误", "不能删除默认班级")
            return

        if messagebox.askyesno("确认删除", f"确定要删除班级 '{self.current_class}' 吗？"):
            del self.classes[self.current_class]
            self.save_all_classes()

            self.current_class = "默认班级"
            self.class_var.set(self.current_class)
            self.class_combo['values'] = list(self.classes.keys())
            self.load_current_class_data()

    def export_class_config(self):
        """导出当前班级配置"""
        filename = filedialog.asksaveasfilename(
            title="导出班级配置",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                config = {
                    "class_name": self.current_class,
                    "config": self.classes[self.current_class]
                }
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("成功", f"班级配置已导出到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出配置时出错: {str(e)}")

    def import_class_config(self):
        """导入班级配置"""
        filename = filedialog.askopenfilename(
            title="导入班级配置",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    config = json.load(f)

                class_name = config.get("class_name")
                class_config = config.get("config")

                if not class_name or not class_config:
                    messagebox.showerror("错误", "配置文件格式不正确")
                    return

                if class_name in self.classes:
                    if not messagebox.askyesno("确认覆盖", f"班级 '{class_name}' 已存在，是否覆盖？"):
                        return

                self.classes[class_name] = class_config
                self.save_all_classes()

                self.class_combo['values'] = list(self.classes.keys())
                messagebox.showinfo("成功", f"已导入班级配置: {class_name}")

            except Exception as e:
                messagebox.showerror("错误", f"导入配置时出错: {str(e)}")

    def import_students_from_file(self):
        """从文件导入学生名单"""
        filename = filedialog.askopenfilename(
            title="选择学生名单文件",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                students = [name.strip() for name in content.split("\n") if name.strip()]

                if students:
                    self.student_text.delete(1.0, tk.END)
                    self.student_text.insert(tk.END, "\n".join(students))
                    messagebox.showinfo("成功", f"已导入 {len(students)} 个学生")
                else:
                    messagebox.showwarning("警告", "文件中没有找到有效的学生名单")

            except Exception as e:
                messagebox.showerror("错误", f"导入学生名单时出错: {str(e)}")

    def migrate_homework(self):
        """作业迁移功能"""

        def perform_migration():
            target_dir = target_entry.get().strip()
            if not target_dir:
                messagebox.showerror("错误", "请选择目标目录")
                return

            if not os.path.exists(target_dir):
                try:
                    os.makedirs(target_dir)
                except Exception as e:
                    messagebox.showerror("错误", f"创建目标目录失败: {str(e)}")
                    return

            source_dir = self.dir_var.get()
            if not source_dir or not os.path.exists(source_dir):
                messagebox.showerror("错误", "源目录不存在，请先设置正确的作业根目录")
                return

            students = [name.strip() for name in self.student_text.get(1.0, tk.END).strip().split("\n") if name.strip()]

            if not students:
                messagebox.showerror("错误", "没有学生名单")
                return

            migration_dialog.destroy()
            self._do_migration(source_dir, target_dir, students)

        migration_dialog = tk.Toplevel(self.root)
        migration_dialog.title("作业迁移")
        migration_dialog.geometry("500x200")
        migration_dialog.resizable(False, False)

        ttk.Label(migration_dialog, text="作业迁移功能", font=("Arial", 12, "bold")).pack(pady=10)
        ttk.Label(migration_dialog, text="将当前班级的作业文件复制到指定目录").pack(pady=5)

        dir_frame = ttk.Frame(migration_dialog)
        dir_frame.pack(fill=tk.X, pady=10, padx=20)

        ttk.Label(dir_frame, text="目标目录:").pack(side=tk.LEFT)
        target_var = tk.StringVar()
        target_entry = ttk.Entry(dir_frame, textvariable=target_var, width=40)
        target_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(dir_frame, text="浏览", command=lambda: target_var.set(filedialog.askdirectory())).pack(side=tk.LEFT)

        button_frame = ttk.Frame(migration_dialog)
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="开始迁移", command=perform_migration).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=migration_dialog.destroy).pack(side=tk.LEFT, padx=10)

        migration_dialog.transient(self.root)
        migration_dialog.grab_set()
        self.root.wait_window(migration_dialog)

    def _do_migration(self, source_dir, target_dir, students):
        """执行作业迁移"""
        migrated_count = 0
        error_count = 0

        for student in students:
            try:
                if self.check_mode == "folder":
                    student_folder = self.find_student_folder(source_dir, student)
                    if student_folder and os.path.isdir(student_folder):
                        target_student_dir = os.path.join(target_dir, student)

                        if os.path.exists(target_student_dir):
                            shutil.rmtree(target_student_dir)

                        shutil.copytree(student_folder, target_student_dir)
                        migrated_count += 1

                else:
                    found_files = self.find_student_files(source_dir, student)
                    if found_files:
                        file_name, file_path = found_files[0]
                        target_file = os.path.join(target_dir, file_name)
                        shutil.copy2(file_path, target_file)
                        migrated_count += 1

            except Exception as e:
                error_count += 1
                print(f"迁移学生 {student} 的作业时出错: {e}")

        messagebox.showinfo("迁移完成",
                            f"作业迁移完成！\n成功迁移: {migrated_count} 个学生\n失败: {error_count} 个")

    def update_extensions(self):
        """更新扩展名显示"""
        for widget in self.ext_frame_inner.winfo_children():
            widget.destroy()

        for i, ext in enumerate(self.file_extensions):
            ext_frame = ttk.Frame(self.ext_frame_inner)
            ext_frame.pack(side=tk.LEFT, padx=2)

            ttk.Label(ext_frame, text=ext).pack(side=tk.LEFT)
            ttk.Button(ext_frame, text="×", width=2,
                       command=lambda e=ext: self.remove_extension(e)).pack(side=tk.LEFT, padx=2)

    def add_extension(self):
        """添加文件扩展名"""

        def save_ext():
            ext = ext_entry.get().strip()
            if ext and not ext.startswith("."):
                ext = "." + ext
            if ext and ext not in self.file_extensions:
                self.file_extensions.append(ext)
                self.update_extensions()
                ext_dialog.destroy()

        ext_dialog = tk.Toplevel(self.root)
        ext_dialog.title("添加文件扩展名")
        ext_dialog.geometry("300x100")
        ext_dialog.resizable(False, False)

        ttk.Label(ext_dialog, text="请输入文件扩展名:").pack(pady=10)
        ext_entry = ttk.Entry(ext_dialog, width=20)
        ext_entry.pack(pady=5)
        ext_entry.focus()

        button_frame = ttk.Frame(ext_dialog)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="确定", command=save_ext).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=ext_dialog.destroy).pack(side=tk.LEFT, padx=10)

        ext_dialog.transient(self.root)
        ext_dialog.grab_set()
        self.root.wait_window(ext_dialog)

    def remove_extension(self, ext):
        """移除文件扩展名"""
        self.file_extensions.remove(ext)
        self.update_extensions()

    def update_mode(self):
        """更新检查模式"""
        self.check_mode = self.mode_var.get()

    def toggle_auto_refresh(self):
        """切换自动刷新"""
        self.auto_refresh = self.refresh_var.get()
        if self.auto_refresh:
            self.start_auto_refresh()
        else:
            self.stop_auto_refresh()

    def update_refresh_interval(self):
        """更新刷新间隔"""
        try:
            new_interval = int(self.interval_var.get())
            if 5 <= new_interval <= 300:
                self.refresh_interval = new_interval
            else:
                self.refresh_interval = 10
                self.interval_var.set("10")
        except ValueError:
            self.refresh_interval = 10
            self.interval_var.set("10")

    def start_auto_refresh(self):
        """开始自动刷新"""
        if self.auto_refresh and not self.refresh_thread:
            self.stop_refresh = False
            self.refresh_thread = threading.Thread(target=self.auto_refresh_worker, daemon=True)
            self.refresh_thread.start()

    def stop_auto_refresh(self):
        """停止自动刷新"""
        self.stop_refresh = True
        self.refresh_thread = None

    def auto_refresh_worker(self):
        """自动刷新工作线程"""
        while self.auto_refresh and not self.stop_refresh:
            time.sleep(self.refresh_interval)
            if self.auto_refresh and not self.stop_refresh:
                self.root.after(0, self.auto_check_homework)

    def auto_check_homework(self):
        """自动检查作业"""
        if not self.dir_var.get() or not os.path.exists(self.dir_var.get()):
            return
        if not self.classes[self.current_class]["students"]:
            return

        # 在自动检查前更新阈值
        self.update_similarity_threshold()

        threading.Thread(target=self._background_check, daemon=True).start()

    def _background_check(self):
        """后台检查"""
        try:
            if self.check_mode == "folder":
                self.check_folder_mode(background=True)
            else:
                self.check_file_mode(background=True)
        except Exception as e:
            print(f"自动检查出错: {e}")

    def browse_directory(self):
        """浏览目录"""
        directory = filedialog.askdirectory()
        if directory:
            self.dir_var.set(directory)

    def save_students(self):
        """保存学生名单"""
        text = self.student_text.get(1.0, tk.END).strip()
        students = [name.strip() for name in text.split("\n") if name.strip()]

        if self.current_class in self.classes:
            self.classes[self.current_class]["students"] = students
            self.save_all_classes()

        messagebox.showinfo("成功", f"已保存 {len(students)} 个学生名单")

    def clear_students(self):
        """清空学生名单"""
        self.student_text.delete(1.0, tk.END)
        if self.current_class in self.classes:
            self.classes[self.current_class]["students"] = []

    def check_homework(self):
        """检查作业 - 在检查前确保更新阈值"""
        if self.is_checking:
            messagebox.showwarning("警告", "正在检查中，请稍候...")
            return

        if not self.dir_var.get() or not os.path.exists(self.dir_var.get()):
            messagebox.showerror("错误", "请先选择有效的作业根目录")
            return

        if not self.classes[self.current_class]["students"]:
            messagebox.showerror("错误", "请先输入学生名单")
            return

        # 在开始检查前更新相似度阈值
        self.update_similarity_threshold()

        self.is_checking = True
        threading.Thread(target=self._perform_check, daemon=True).start()

    def _perform_check(self):
        """执行检查"""
        self.root.after(0, self.clear_results)

        submitted_count = 0
        try:
            if self.check_mode == "folder":
                submitted_count = self.check_folder_mode()
            else:
                submitted_count = self.check_file_mode()
        except Exception as e:
            print(f"检查过程中出错: {e}")
        finally:
            self.root.after(0, lambda: self.update_stats(submitted_count))
            self.is_checking = False

    def clear_results(self):
        """清空结果"""
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

    def update_stats(self, submitted_count):
        """更新统计信息"""
        students = self.classes[self.current_class]["students"]
        total_count = len(students)
        not_submitted_count = total_count - submitted_count
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.stats_label.config(
            text=f"总计: {total_count}人 | 已提交: {submitted_count}人 | 未提交: {not_submitted_count}人"
        )
        self.time_label.config(text=f"最后检查: {current_time}")

    def check_folder_mode(self, background=False):
        """文件夹模式检查"""
        submitted_count = 0
        students = self.classes[self.current_class]["students"]
        root_dir = self.dir_var.get()

        results = []
        student_files = {}

        for student in students:
            student_folder = self.find_student_folder(root_dir, student)

            if not student_folder or not os.path.isdir(student_folder):
                results.append((student, "未提交", "0%", "未找到学生文件夹", "未知", 'not_submitted'))
                continue

            found_files = []
            for file in os.listdir(student_folder):
                file_path = os.path.join(student_folder, file)
                if os.path.isfile(file_path) and any(
                        file.lower().endswith(ext.lower()) for ext in self.file_extensions):
                    found_files.append((file, file_path))

            if found_files:
                file_name, file_path = found_files[0]
                student_files[student] = file_path
                file_time = self.get_file_modification_time(file_path)
                results.append((student, "已提交", "0%", f"找到文件: {file_name}", file_time, 'submitted', file_path))
                submitted_count += 1
            else:
                results.append((student, "未提交", "0%", "文件夹中没有指定扩展名的文件", "未知", 'not_submitted'))

        # 进行抄袭检测
        plagiarism_results = {}
        if student_files:
            plagiarism_results = self.check_plagiarism(student_files)

        # 更新结果，添加抄袭信息
        final_results = []
        for result in results:
            student, status, similarity, details, file_time, tag, *file_path = result
            file_path = file_path[0] if file_path else None

            if student in plagiarism_results:
                plagiarism_info = plagiarism_results[student]
                similarity = f"{plagiarism_info['similarity']}%"

                # 使用当前阈值判定抄袭
                if plagiarism_info['similarity'] >= self.similarity_threshold:
                    if plagiarism_info['type'] == 'identical':
                        other_students = ", ".join(plagiarism_info['other_students'])
                        details = f"{details} (与{other_students}完全相同，MD5相同)"
                        tag = 'suspected_plagiarism'
                        status = "疑似抄袭"
                    else:
                        other_students = ", ".join(plagiarism_info['other_students'][:3])
                        if len(plagiarism_info['other_students']) > 3:
                            other_students += f" 等{len(plagiarism_info['other_students'])}人"
                        details = f"{details} (与{other_students}相似度{plagiarism_info['similarity']}%)"
                        tag = 'suspected_plagiarism'
                        status = "疑似抄袭"
                else:
                    # 相似度低于阈值，只显示信息但不改变状态
                    other_students = ", ".join(plagiarism_info['other_students'][:2])
                    if len(plagiarism_info['other_students']) > 2:
                        other_students += f" 等{len(plagiarism_info['other_students'])}人"
                    details = f"{details} (与{other_students}相似度{plagiarism_info['similarity']}%)"

            final_results.append((student, status, similarity, details, file_time, tag))

        # 按状态排序
        final_results.sort(key=lambda x: (0 if x[1] in ["已提交", "疑似抄袭"] else 1, x[0]))

        if not background:
            for result in final_results:
                self.root.after(0, lambda r=result: self.add_result_item(*r))

        return submitted_count

    def check_file_mode(self, background=False):
        """文件模式检查"""
        submitted_count = 0
        students = self.classes[self.current_class]["students"]
        root_dir = self.dir_var.get()

        results = []
        student_files = {}

        for student in students:
            found_files = self.find_student_files(root_dir, student)

            if found_files:
                file_name, file_path = found_files[0]
                student_files[student] = file_path
                file_time = self.get_file_modification_time(file_path)
                results.append((student, "已提交", "0%", f"找到文件: {file_name}", file_time, 'submitted', file_path))
                submitted_count += 1
            else:
                results.append((student, "未提交", "0%", "未找到学生文件", "未知", 'not_submitted'))

        # 进行抄袭检测
        plagiarism_results = {}
        if student_files:
            plagiarism_results = self.check_plagiarism(student_files)

        # 更新结果，添加抄袭信息
        final_results = []
        for result in results:
            student, status, similarity, details, file_time, tag, *file_path = result
            file_path = file_path[0] if file_path else None

            if student in plagiarism_results:
                plagiarism_info = plagiarism_results[student]
                similarity = f"{plagiarism_info['similarity']}%"

                # 使用当前阈值判定抄袭
                if plagiarism_info['similarity'] >= self.similarity_threshold:
                    if plagiarism_info['type'] == 'identical':
                        other_students = ", ".join(plagiarism_info['other_students'])
                        details = f"{details} (与{other_students}完全相同，MD5相同)"
                        tag = 'suspected_plagiarism'
                        status = "疑似抄袭"
                    else:
                        other_students = ", ".join(plagiarism_info['other_students'][:3])
                        if len(plagiarism_info['other_students']) > 3:
                            other_students += f" 等{len(plagiarism_info['other_students'])}人"
                        details = f"{details} (与{other_students}相似度{plagiarism_info['similarity']}%)"
                        tag = 'suspected_plagiarism'
                        status = "疑似抄袭"
                else:
                    # 相似度低于阈值，只显示信息但不改变状态
                    other_students = ", ".join(plagiarism_info['other_students'][:2])
                    if len(plagiarism_info['other_students']) > 2:
                        other_students += f" 等{len(plagiarism_info['other_students'])}人"
                    details = f"{details} (与{other_students}相似度{plagiarism_info['similarity']}%)"

            final_results.append((student, status, similarity, details, file_time, tag))

        # 按状态排序
        final_results.sort(key=lambda x: (0 if x[1] in ["已提交", "疑似抄袭"] else 1, x[0]))

        if not background:
            for result in final_results:
                self.root.after(0, lambda r=result: self.add_result_item(*r))

        return submitted_count

    def add_result_item(self, student, status, similarity, details, file_time, tag):
        """添加结果项"""
        self.result_tree.insert("", tk.END, values=(student, status, similarity, details, file_time), tags=(tag,))

    def on_closing(self):
        """关闭程序时的处理"""
        self.stop_auto_refresh()
        self.save_current_class()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = HomeworkCheckSystem(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()