import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import keyboard
import sys

# 실행 파일(exe)로 빌드되었을 때와 Python 스크립트로 실행될 때의 경로를 대응
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(application_path, "shortcuts.json")

def load_data():
    """로컬 JSON 파일에서 단축어 데이터를 불러옵니다."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_data(data):
    """단축어 데이터를 로컬 JSON 파일에 저장합니다."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class TextMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("실시간 텍스트 대치 매크로")
        self.root.geometry("450x400")
        self.root.resizable(False, False)
        
        self.is_hidden = False
        
        # 'X' 버튼(창 닫기)을 눌렀을 때 완전히 꺼지지 않고 숨기기 함수 호출
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # 언제 어디서든 Ctrl+Shift+M을 누르면 창이 나타나거나 숨으면서 토글됨
        keyboard.add_hotkey('ctrl+shift+m', self.toggle_window)
        
        self.data = load_data()
        
        self.setup_ui()
        self.apply_hooks()

    def hide_window(self):
        """프로그램을 화면에서 숨기고 백그라운드로 보냅니다."""
        self.is_hidden = True
        self.root.withdraw()
        if not hasattr(self, 'hide_notified'):
            messagebox.showinfo("백그라운드 실행 중", "창이 닫히지 않고 백그라운드에서 계속 동작중입니다!\n\n설정 창을 다시 열려면 키보드에서\n[ Ctrl + Shift + M ] 을 누르세요.")
            self.hide_notified = True

    def toggle_window(self):
        """단축키로 창 숨김/표시를 전환합니다 (스레드 안전을 위해 after 사용)"""
        self.root.after(0, self._toggle)

    def _toggle(self):
        if self.is_hidden:
            self.is_hidden = False
            self.root.deiconify() # 창 다시 표시
            self.root.lift()      # 최상단으로 끌어올림
            self.root.focus_force()
        else:
            self.hide_window()

    def quit_app(self):
        """프로그램을 완전히 종료합니다."""
        if messagebox.askyesno("완전 종료", "마우스/비밀번호 매크로를 완전히 종료하시겠습니까?\n종료하면 더 이상 대치 기능이 동작하지 않습니다."):
            keyboard.unhook_all()
            self.root.destroy()

    def setup_ui(self):
        """GUI 요소를 구성합니다."""
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 리스트박스 (Treeview) 영역
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        columns = ("short", "long")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)
        self.tree.heading("short", text="단축어")
        self.tree.heading("long", text="대체어")
        self.tree.column("short", width=100, anchor=tk.CENTER)
        self.tree.column("long", width=300, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # 2. 입력 폼 영역
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(form_frame, text="단축어 :").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_short = ttk.Entry(form_frame, width=15)
        self.entry_short.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(form_frame, text="대체어 :").grid(row=1, column=0, sticky=tk.NW, pady=5)
        self.entry_long = tk.Text(form_frame, width=40, height=4, font=("TkDefaultFont", 10))
        self.entry_long.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # 3. 버튼 영역
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="저장 / 수정", command=self.save_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="삭제", command=self.delete_item).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="완전 종료", command=self.quit_app).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="입력창 초기화", command=self.clear_form).pack(side=tk.RIGHT, padx=5)

        self.refresh_list()

    def refresh_list(self):
        """Treeview의 데이터를 갱신합니다."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for short, long in self.data.items():
            # 리스트박스(표)에서는 줄바꿈 기호를 화살표로 보여주어 한 줄로 예쁘게 표시
            display_long = long.replace("\n", " ↵ ")
            self.tree.insert("", tk.END, values=(short, display_long))

    def on_select(self, event):
        """목록에서 항목을 선택했을 때 입력 폼에 표시합니다."""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            short = item['values'][0] # 리스트박스의 short 키를 이용해
            long_original = self.data[str(short)] # 진짜 원본(줄바꿈 포함된) 텍스트를 가져옴
            self.clear_form()
            self.entry_short.insert(0, short)
            self.entry_long.insert("1.0", long_original)

    def clear_form(self):
        """입력 창을 비웁니다."""
        self.entry_short.delete(0, tk.END)
        self.entry_long.delete("1.0", tk.END)

    def save_item(self):
        """단축어와 대체어를 저장하거나 수정합니다."""
        short = self.entry_short.get().strip()
        long = self.entry_long.get("1.0", tk.END).strip()  # Text 위젯 전체 텍스트 가져오기
        
        if not short or not long:
            messagebox.showwarning("입력 오류", "단축어와 대체어를 모두 입력해 주세요.")
            return
            
        self.data[short] = long
        save_data(self.data)
        self.refresh_list()
        self.clear_form()
        self.apply_hooks()
        messagebox.showinfo("완료", "저장되었습니다.")

    def delete_item(self):
        """선택된 항목을 삭제합니다."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("선택 오류", "목록에서 삭제할 항목을 선택해 주세요.")
            return
            
        item = self.tree.item(selected[0])
        short = item['values'][0]
        
        if messagebox.askyesno("삭제 확인", f"단축어 '{short}'을(를) 삭제하시겠습니까?"):
            if str(short) in self.data:
                del self.data[str(short)]
                save_data(self.data)
                self.refresh_list()
                self.clear_form()
                self.apply_hooks()
                messagebox.showinfo("완료", "삭제되었습니다.")

    def apply_hooks(self):
        """현재 등록된 단축어 목록으로 키보드 후킹을 새롭게 갱신합니다."""
        keyboard.unhook_all()
        for short, long in self.data.items():
            # 사용자가 short 입력 후 Space 또는 Enter (트리거) 입력 시 long으로 대치 (기본 내장 기능)
            keyboard.add_abbreviation(short, long)

def main():
    root = tk.Tk()
    app = TextMacroApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
