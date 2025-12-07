import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import json
import threading
import os
import time

# ==================== НАСТРОЙКИ ====================

MAX_LINES_PER_FILE = 3000000  # По 3 миллиона строк в файле

class LargeJSONSplitterApp:
    
    def __init__(self, root):
        self.root = root
        self.root.title("JSON Deduplicator & Splitter (Stream Mode)")
        self.root.geometry("700x500")
        
        self.selected_file = ""
        self.is_running = False
        
        self.create_widgets()
    
    def create_widgets(self):
        # Фрейм управления
        ctrl_frame = tk.Frame(self.root, pady=15, padx=15)
        ctrl_frame.pack(fill=tk.X)
        
        self.btn_load = ttk.Button(ctrl_frame, text="1. Выбрать гигантский JSON", command=self.select_file)
        self.btn_load.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.btn_run = ttk.Button(ctrl_frame, text="2. Запустить обработку", command=self.start_thread, state=tk.DISABLED)
        self.btn_run.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Инфо о файле
        self.lbl_file = tk.Label(self.root, text="Файл не выбран", fg="gray")
        self.lbl_file.pack(pady=5)
        
        # Прогресс
        progress_frame = tk.LabelFrame(self.root, text="Прогресс", padx=10, pady=10)
        progress_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)
        
        self.lbl_status = tk.Label(progress_frame, text="Ожидание...")
        self.lbl_status.pack(anchor=tk.W, pady=(5,0))
        
        # Лог
        log_frame = tk.LabelFrame(self.root, text="Лог", padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED, font=("Consolas", 9), yscrollcommand=scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            self.selected_file = path
            size_gb = os.path.getsize(path) / (1024**3)
            self.lbl_file.config(text=f"{path} ({size_gb:.2f} GB)", fg="black")
            self.btn_run.config(state=tk.NORMAL)
            self.log(f"Выбран файл: {os.path.basename(path)}")

    def start_thread(self):
        if not self.selected_file:
            return
        
        self.is_running = True
        self.btn_load.config(state=tk.DISABLED)
        self.btn_run.config(state=tk.DISABLED)
        
        t = threading.Thread(target=self.process_file, daemon=True)
        t.start()

    def process_file(self):
        try:
            input_path = self.selected_file
            file_dir = os.path.dirname(input_path)
            file_name = os.path.splitext(os.path.basename(input_path))[0]
            
            # Набор хешей (или самих строк) заголовков для проверки дублей
            # Используем set, так как поиск в нем O(1).
            # 98 млн строк в set займут около 4-6 ГБ RAM, что влезает в 16 ГБ.
            seen_titles = set()
            
            total_processed = 0
            unique_count = 0
            duplicates_count = 0
            file_part_num = 1
            current_part_lines = 0
            
            # Получаем размер файла для прогресс-бара
            total_size = os.path.getsize(input_path)
            bytes_read = 0
            
            self.log("🚀 Старт обработки...")
            
            # Открываем первый файл для записи
            output_path = os.path.join(file_dir, f"{file_name}_part{file_part_num}.json")
            out_f = open(output_path, 'w', encoding='utf-8')
            self.log(f"   Создан: {os.path.basename(output_path)}")
            
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as in_f:
                for line in in_f:
                    bytes_read += len(line.encode('utf-8')) # Примерный подсчет байт
                    line = line.strip()
                    
                    if not line:
                        continue
                        
                    try:
                        # Парсим
                        record = json.loads(line)
                        
                        # Ищем ключ (Наименование или title)
                        title = None
                        if "title" in record:
                            title = str(record["title"]).strip()
                        elif "Наименование" in record:
                            title = str(record["Наименование"]).strip()
                        
                        # Логика дубликатов
                        if title:
                            if title in seen_titles:
                                duplicates_count += 1
                                continue # Пропускаем, это дубль
                            else:
                                seen_titles.add(title)
                        
                        # Если дошли сюда — запись уникальная.
                        # Записываем СРАЗУ в файл (не храним объект в памяти)
                        # ensure_ascii=False чтобы русские буквы не превращались в \uXXXX
                        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        
                        unique_count += 1
                        current_part_lines += 1
                        
                        # Проверка на разбивку
                        if current_part_lines >= MAX_LINES_PER_FILE:
                            out_f.close()
                            self.log(f"   ✓ Часть {file_part_num} готова ({current_part_lines} строк)")
                            
                            file_part_num += 1
                            current_part_lines = 0
                            output_path = os.path.join(file_dir, f"{file_name}_part{file_part_num}.json")
                            out_f = open(output_path, 'w', encoding='utf-8')
                            self.log(f"   Создан: {os.path.basename(output_path)}")
                            
                    except json.JSONDecodeError:
                        pass # Просто игнорируем битые строки
                    
                    total_processed += 1
                    
                    # Обновление GUI раз в 50000 строк
                    if total_processed % 50000 == 0:
                        progress = (bytes_read / total_size) * 100
                        self.progress_var.set(progress)
                        self.lbl_status.config(text=f"Обработано: {total_processed:,} | Уникальных: {unique_count:,} | Дубликатов: {duplicates_count:,}")
            
            # Закрываем последний файл
            out_f.close()
            if current_part_lines == 0:
                # Если последний файл оказался пустым (ровное деление), удалим его
                os.remove(output_path)
            else:
                self.log(f"   ✓ Часть {file_part_num} готова ({current_part_lines} строк)")

            self.progress_var.set(100)
            self.lbl_status.config(text="Готово!")
            self.log("="*40)
            self.log(f"✅ УСПЕШНО ЗАВЕРШЕНО")
            self.log(f"Всего строк обработано: {total_processed:,}")
            self.log(f"Уникальных записей: {unique_count:,}")
            self.log(f"Найдено дубликатов: {duplicates_count:,}")
            
            messagebox.showinfo("Готово", f"Обработка завершена.\nРезультат разбит на {file_part_num} файлов.")

        except Exception as e:
            self.log(f"❌ ОШИБКА: {e}")
            messagebox.showerror("Ошибка", str(e))
        
        finally:
            self.is_running = False
            self.btn_load.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = LargeJSONSplitterApp(root)
    root.mainloop()