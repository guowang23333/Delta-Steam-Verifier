import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import openpyxl


def _base_dir() -> str:
    """资源读取目录：打包后为 _MEIPASS，开发时为脚本目录"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _work_dir() -> str:
    """可写工作目录：打包后为 exe 所在目录，开发时为脚本目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# ---------------------------
# 账号管理
# ---------------------------
def load_accounts_from_excel(file_path: str) -> list[dict]:
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active
    headers = [str(c.value).strip().lower() for c in next(ws.iter_rows(min_row=1, max_row=1))]
    if 'username' not in headers or 'password' not in headers:
        raise ValueError("Excel 文件需包含 username 和 password 列")
    ui = headers.index('username')
    pi = headers.index('password')
    accounts = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        u, p = row[ui], row[pi]
        if u and p:
            accounts.append({'username': str(u).strip(), 'password': str(p).strip()})
    return accounts


def save_accounts_to_config(accounts: list[dict]):
    config_path = os.path.join(_work_dir(), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    data['accounts'] = accounts
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_accounts_from_config() -> list[dict]:
    config_path = os.path.join(_work_dir(), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [a for a in data.get('accounts', []) if a.get('username')]


# ---------------------------
# 主界面
# ---------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Delta Steam Verifier")
        self.geometry("820x560")
        self.resizable(False, False)
        self._log_queue: queue.Queue = queue.Queue()
        self._running = False
        self._build_ui()
        self._load_accounts()
        self._poll_log()

    def _build_ui(self):
        # 左侧账号面板
        left = tk.Frame(self, width=320)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 5), pady=10)
        left.pack_propagate(False)

        tk.Label(left, text="账号列表", font=("", 11, "bold")).pack(anchor="w")

        # 账号表格
        cols = ("username", "password")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=18)
        self.tree.heading("username", text="账号")
        self.tree.heading("password", text="密码")
        self.tree.column("username", width=140)
        self.tree.column("password", width=140)
        sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.LEFT, fill=tk.Y)

        # 右侧操作面板
        right = tk.Frame(self)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=10)

        # 按钮行
        btn_frame = tk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=(6, 0))

        tk.Button(btn_frame, text="导入 Excel", width=10, command=self._import_excel).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(btn_frame, text="手动添加", width=10, command=self._add_account).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(btn_frame, text="删除选中", width=10, command=self._delete_selected).pack(side=tk.LEFT)

        # 日志区
        tk.Label(right, text="运行日志", font=("", 11, "bold")).pack(anchor="w")
        self.log_box = tk.Text(right, state=tk.DISABLED, bg="#1e1e1e", fg="#d4d4d4",
                               font=("Courier", 10), wrap=tk.WORD)
        self.log_box.pack(fill=tk.BOTH, expand=True)

        log_sb = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=log_sb.set)
        log_sb.place(relx=1, rely=0, relheight=1, anchor="ne")

        # 底部控制栏
        ctrl = tk.Frame(right)
        ctrl.pack(fill=tk.X, pady=(6, 0))

        self.start_btn = tk.Button(ctrl, text="▶  开始运行", bg="#0e7a0d", fg="white",
                                   font=("", 10, "bold"), width=14, command=self._start)
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = tk.Button(ctrl, text="■  停止", bg="#a00", fg="white",
                                  font=("", 10, "bold"), width=10,
                                  state=tk.DISABLED, command=self._stop)
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))

        tk.Button(ctrl, text="清空日志", command=self._clear_log).pack(side=tk.RIGHT)

    # ---------------------------
    # 账号操作
    # ---------------------------
    def _load_accounts(self):
        try:
            accounts = load_accounts_from_config()
            self.tree.delete(*self.tree.get_children())
            for a in accounts:
                self.tree.insert("", tk.END, values=(a['username'], a['password']))
        except Exception as e:
            messagebox.showerror("错误", f"加载账号失败: {e}")

    def _import_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel 文件", "*.xlsx *.xls")])
        if not path:
            return
        try:
            accounts = load_accounts_from_excel(path)
            for a in accounts:
                self.tree.insert("", tk.END, values=(a['username'], a['password']))
            self._sync_accounts()
            self._log(f"已导入 {len(accounts)} 个账号")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))

    def _add_account(self):
        win = tk.Toplevel(self)
        win.title("添加账号")
        win.geometry("280x130")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="账号").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        u_var = tk.StringVar()
        tk.Entry(win, textvariable=u_var, width=22).grid(row=0, column=1, padx=10)

        tk.Label(win, text="密码").grid(row=1, column=0, padx=10, pady=4, sticky="e")
        p_var = tk.StringVar()
        tk.Entry(win, textvariable=p_var, show="*", width=22).grid(row=1, column=1, padx=10)

        def confirm():
            u, p = u_var.get().strip(), p_var.get().strip()
            if not u or not p:
                messagebox.showwarning("提示", "账号和密码不能为空", parent=win)
                return
            self.tree.insert("", tk.END, values=(u, p))
            self._sync_accounts()
            win.destroy()

        tk.Button(win, text="确认", command=confirm, width=10).grid(row=2, column=0, columnspan=2, pady=10)

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        for item in selected:
            self.tree.delete(item)
        self._sync_accounts()

    def _sync_accounts(self):
        accounts = [
            {'username': self.tree.item(i)['values'][0],
             'password': self.tree.item(i)['values'][1]}
            for i in self.tree.get_children()
        ]
        save_accounts_to_config(accounts)

    # ---------------------------
    # 运行控制
    # ---------------------------
    def _start(self):
        accounts = [
            {'username': self.tree.item(i)['values'][0],
             'password': self.tree.item(i)['values'][1]}
            for i in self.tree.get_children()
        ]
        if not accounts:
            messagebox.showwarning("提示", "请先添加账号")
            return

        self._running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._log("=== 开始运行 ===")

        self._thread = threading.Thread(target=self._run_task, args=(accounts,), daemon=True)
        self._thread.start()

    def _stop(self):
        self._running = False
        self._log("=== 用户已停止 ===")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def _run_task(self, accounts):
        try:
            import main as core
            core._log_callback = self._log

            for idx, acc in enumerate(accounts):
                if not self._running:
                    break
                self._log(f"\n{'='*36}")
                self._log(f"处理账号 ({idx+1}/{len(accounts)}): {acc['username']}")
                try:
                    core.login_steam(acc['username'], acc['password'])
                    core.launch_game()
                    time.sleep(15)
                    ban_info = core.capture_ban_info(acc['username'])

                    log_msg = f"{datetime.now()}, {acc['username']}, "
                    if ban_info["is_banned"]:
                        log_msg += f"封禁 | 时长:{ban_info['duration']} | 解封:{ban_info['unban_time']}"
                        self._log(f"!!! 封禁警报 !!! {ban_info['raw_text'][:50]}")
                    else:
                        log_msg += "正常"
                        self._log("账号状态：正常")

                    with open("result.log", "a", encoding="utf-8") as f:
                        f.write(log_msg + "\n")
                except Exception as e:
                    self._log(f"流程异常: {e}")
                finally:
                    core.logout_steam()
        finally:
            self._running = False
            self.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            self._log("=== 运行结束 ===")

    # ---------------------------
    # 日志
    # ---------------------------
    def _log(self, msg: str):
        self._log_queue.put(msg)

    def _poll_log(self):
        while not self._log_queue.empty():
            msg = self._log_queue.get_nowait()
            self.log_box.config(state=tk.NORMAL)
            self.log_box.insert(tk.END, msg + "\n")
            self.log_box.see(tk.END)
            self.log_box.config(state=tk.DISABLED)
        self.after(100, self._poll_log)

    def _clear_log(self):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.config(state=tk.DISABLED)


if __name__ == "__main__":
    import pytesseract

    # 设置 Tesseract 路径
    pytesseract.pytesseract.tesseract_cmd = os.path.join(
        _base_dir(), "Tesseract-OCR", "tesseract.exe"
    )

    # 捕获配置加载失败，弹窗提示而不是静默崩溃
    try:
        from config_loader import config  # noqa: F401 触发初始化
    except Exception as e:
        import tkinter as _tk
        _r = _tk.Tk()
        _r.withdraw()
        from tkinter import messagebox as _mb
        _mb.showerror("配置错误", f"config.json 加载失败:\n{e}")
        _r.destroy()
        raise SystemExit(1)

    app = App()
    app.mainloop()
