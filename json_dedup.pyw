"""
Удаление дубликатов из огромных NDJSON файлов
Оптимизировано для 100+ млн строк при 16 ГБ RAM

Особенности:
- Хранит только множество title (не весь объект)
- Пишет сразу на диск, не накапливает в памяти
- Разбивает на части по 3 млн строк
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import json
import time
from datetime import datetime


# ==================== НАСТРОЙКИ ====================

MAX_LINES_PER_FILE = 3_000_000  # 3 миллиона строк на файл


# ==================== ГЛАВНЫЙ КЛАСС ====================

class JSONDedupApp:
    
    def __init__(self, root):
        self.root = root
        self.root.title("JSON Дедупликатор (для огромных файлов)")
        self.root.geometry("800x550")
        self.root.resizable(True, True)
        
        self.selected_file = None
        self.is_processing = False
        self.stop_flag = False
        
        self.create_widgets()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === Кнопки ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_load = ttk.Button(
            btn_frame, text="📂 Выбрать файл", command=self.load_file
        )
        self.btn_load.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_process = ttk.Button(
            btn_frame, text="🔧 Удалить дубликаты", command=self.start_processing,
            state=tk.DISABLED
        )
        self.btn_process.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_stop = ttk.Button(
            btn_frame, text="⏹ Стоп", command=self.stop_processing,
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT)
        
        # === Информация о файле ===
        self.file_label = ttk.Label(main_frame, text="Файл не выбран", font=("Arial", 10))
        self.file_label.pack(anchor=tk.W, pady=(0, 10))
        
        # === Прогресс ===
        progress_frame = ttk.LabelFrame(main_frame, text="Прогресс", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(progress_frame, text="Ожидание...")
        self.status_label.pack(anchor=tk.W)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        self.stats_label = ttk.Label(progress_frame, text="")
        self.stats_label.pack(anchor=tk.W, pady=(5, 0))
        
        # === Лог ===
        log_frame = ttk.LabelFrame(main_frame, text="Лог", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            log_frame, height=15, font=("Consolas", 9),
            yscrollcommand=log_scroll.set, state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)
        
        # Цветные теги
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("info", foreground="blue")
        self.log_text.tag_config("warn", foreground="orange")
    
    def log(self, message, tag=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def load_file(self):
        if self.is_processing:
            return
        
        file_path = filedialog.askopenfilename(
            title="Выберите JSON файл",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            self.selected_file = file_path
            size_gb = os.path.getsize(file_path) / (1024**3)
            self.file_label.config(
                text=f"📄 {os.path.basename(file_path)} ({size_gb:.2f} GB)"
            )
            self.btn_process.config(state=tk.NORMAL)
            self.log(f"Выбран файл: {os.path.basename(file_path)}", "info")
    
    def start_processing(self):
        if not self.selected_file or self.is_processing:
            return
        
        self.is_processing = True
        self.stop_flag = False
        self.btn_load.config(state=tk.DISABLED)
        self.btn_process.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        thread = threading.Thread(target=self.process_file, daemon=True)
        thread.start()
    
    def stop_processing(self):
        self.stop_flag = True
        self.log("⏹ Остановка...", "warn")
    
    def process_file(self):
        """
        Главный алгоритм:
        1. Читаем строку за строкой
        2. Извлекаем title/Наименование
        3. Если новый — сразу пишем в текущий выходной файл
        4. Когда набралось 3 млн — создаём новый файл
        
        В памяти храним ТОЛЬКО set() с title (строки ~50 байт каждая)
        98 млн уникальных title ≈ 5-8 ГБ RAM — должно влезть
        """
        try:
            start_time = time.time()
            
            file_path = self.selected_file
            file_dir = os.path.dirname(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            
            self.root.after(0, lambda: self.log("Подсчёт строк...", "info"))
            
            # Подсчёт общего количества строк
            total_lines = 0
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for _ in f:
                    total_lines += 1
            
            self.root.after(0, lambda: self.log(f"Всего строк: {total_lines:,}", "info"))
            self.root.after(0, lambda: self.log("Начинаю обработку...", "info"))
            
            # === ГЛАВНЫЙ ПРОХОД ===
            seen_titles = set()  # Только это хранится в памяти!
            
            current_part = 1
            lines_in_current_file = 0
            current_output = None
            output_file_path = None
            
            processed = 0
            duplicates = 0
            errors = 0
            written = 0
            
            def open_new_output():
                nonlocal current_output, output_file_path, current_part, lines_in_current_file
                if current_output:
                    current_output.close()
                output_file_path = os.path.join(
                    file_dir, f"{file_name}_dedup_part{current_part}.json"
                )
                current_output = open(output_file_path, 'w', encoding='utf-8')
                lines_in_current_file = 0
                self.root.after(0, lambda p=current_part: 
                    self.log(f"📝 Создан файл: part{p}", "info"))
                current_part += 1
            
            # Открываем первый файл
            open_new_output()
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                for line in infile:
                    if self.stop_flag:
                        break
                    
                    processed += 1
                    
                    # Обновление UI каждые 100к строк
                    if processed % 100_000 == 0:
                        progress = (processed / total_lines) * 100
                        self.root.after(0, lambda p=progress, proc=processed, dup=duplicates, wr=written:
                            self.update_progress(p, proc, dup, wr, total_lines))
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Парсим JSON
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        errors += 1
                        continue
                    
                    # Извлекаем title
                    title = None
                    if 'title' in record:
                        title = record.get('title', '')
                    elif 'Наименование' in record:
                        title = record.get('Наименование', '')
                    
                    # Нормализация title
                    if title is not None:
                        if not isinstance(title, str):
                            title = str(title)
                        title = title.strip()
                        
                        # Проверка на дубликат
                        if title in seen_titles:
                            duplicates += 1
                            continue
                        
                        seen_titles.add(title)
                    
                    # Записываем в выходной файл
                    current_output.write(line + '\n')
                    written += 1
                    lines_in_current_file += 1
                    
                    # Если достигли лимита — новый файл
                    if lines_in_current_file >= MAX_LINES_PER_FILE:
                        open_new_output()
            
            # Закрываем последний файл
            if current_output:
                current_output.close()
            
            elapsed = time.time() - start_time
            
            # Финальная статистика
            self.root.after(0, lambda: self.update_progress(100, processed, duplicates, written, total_lines))
            self.root.after(0, lambda: self.log("=" * 50, None))
            self.root.after(0, lambda: self.log(f"✅ Готово за {elapsed:.1f} сек", "success"))
            self.root.after(0, lambda: self.log(f"   Обработано строк: {processed:,}", "success"))
            self.root.after(0, lambda: self.log(f"   Дубликатов удалено: {duplicates:,}", "success"))
            self.root.after(0, lambda: self.log(f"   Уникальных записей: {written:,}", "success"))
            self.root.after(0, lambda: self.log(f"   Ошибок парсинга: {errors:,}", "warn" if errors else None))
            self.root.after(0, lambda: self.log(f"   Создано файлов: {current_part - 1}", "success"))
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Готово!",
                f"Обработка завершена!\n\n"
                f"Всего строк: {processed:,}\n"
                f"Дубликатов: {duplicates:,}\n"
                f"Уникальных: {written:,}\n"
                f"Файлов создано: {current_part - 1}\n"
                f"Время: {elapsed:.1f} сек"
            ))
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Ошибка: {str(e)}", "error"))
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        
        finally:
            self.root.after(0, self.finish_processing)
    
    def update_progress(self, percent, processed, duplicates, written, total):
        self.progress_var.set(percent)
        self.status_label.config(text=f"Обработано: {processed:,} / {total:,}")
        self.stats_label.config(
            text=f"✓ Уникальных: {written:,} | ✗ Дубликатов: {duplicates:,}"
        )
    
    def finish_processing(self):
        self.is_processing = False
        self.btn_load.config(state=tk.NORMAL)
        self.btn_process.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = JSONDedupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()