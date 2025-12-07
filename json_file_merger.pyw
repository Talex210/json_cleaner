import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from datetime import datetime


class JSONMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON File Merger (NDJSON)")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        self.files = []
        self.is_processing = False
        
        self.create_widgets()
    
    def create_widgets(self):
        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Кнопки управления
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_load = ttk.Button(
            btn_frame, 
            text="📂 Загрузить файлы", 
            command=self.load_files
        )
        self.btn_load.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_clear = ttk.Button(
            btn_frame, 
            text="🗑️ Очистить список", 
            command=self.clear_files
        )
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_merge = ttk.Button(
            btn_frame, 
            text="🔗 Склеить файлы", 
            command=self.start_merge
        )
        self.btn_merge.pack(side=tk.LEFT)
        
        # Список файлов
        files_label = ttk.Label(main_frame, text="Выбранные файлы:")
        files_label.pack(anchor=tk.W)
        
        # Фрейм для списка с прокруткой
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        scrollbar_y = ttk.Scrollbar(list_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.files_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            selectmode=tk.EXTENDED,
            font=("Consolas", 9)
        )
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_y.config(command=self.files_listbox.yview)
        scrollbar_x.config(command=self.files_listbox.xview)
        
        # Информация о файлах
        self.info_label = ttk.Label(main_frame, text="Файлов: 0 | Общий размер: 0 MB")
        self.info_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Прогресс-бар
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(progress_frame, text="Прогресс:").pack(anchor=tk.W)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        self.progress_label = ttk.Label(progress_frame, text="0% | Строк: 0")
        self.progress_label.pack(anchor=tk.E)
        
        # Лог
        log_label = ttk.Label(main_frame, text="Лог операций:")
        log_label.pack(anchor=tk.W)
        
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        log_scrollbar = ttk.Scrollbar(log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            log_frame,
            height=8,
            yscrollcommand=log_scrollbar.set,
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scrollbar.config(command=self.log_text.yview)
        
        # Теги для цветов в логе
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("info", foreground="blue")
    
    def log(self, message, tag=None):
        """Добавить сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        if tag:
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        else:
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def load_files(self):
        """Загрузить JSON файлы"""
        if self.is_processing:
            messagebox.showwarning("Внимание", "Дождитесь завершения текущей операции")
            return
        
        files = filedialog.askopenfilenames(
            title="Выберите JSON файлы",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if files:
            self.files = list(files)
            self.files.sort()  # Сортировка по имени
            self.update_file_list()
            self.log(f"Загружено файлов: {len(self.files)}", "info")
    
    def clear_files(self):
        """Очистить список файлов"""
        if self.is_processing:
            messagebox.showwarning("Внимание", "Дождитесь завершения текущей операции")
            return
        
        self.files = []
        self.update_file_list()
        self.progress_var.set(0)
        self.progress_label.config(text="0% | Строк: 0")
        self.log("Список файлов очищен", "info")
    
    def update_file_list(self):
        """Обновить отображение списка файлов"""
        self.files_listbox.delete(0, tk.END)
        
        total_size = 0
        for f in self.files:
            size = os.path.getsize(f)
            total_size += size
            size_mb = size / (1024 * 1024)
            name = os.path.basename(f)
            self.files_listbox.insert(tk.END, f"{name} ({size_mb:.2f} MB)")
        
        total_mb = total_size / (1024 * 1024)
        total_gb = total_size / (1024 * 1024 * 1024)
        
        if total_gb >= 1:
            size_str = f"{total_gb:.2f} GB"
        else:
            size_str = f"{total_mb:.2f} MB"
        
        self.info_label.config(text=f"Файлов: {len(self.files)} | Общий размер: {size_str}")
    
    def start_merge(self):
        """Начать процесс слияния"""
        if self.is_processing:
            messagebox.showwarning("Внимание", "Процесс уже выполняется")
            return
        
        if len(self.files) < 1:
            messagebox.showwarning("Внимание", "Выберите файлы для слияния")
            return
        
        # Выбор файла для сохранения
        output_file = filedialog.asksaveasfilename(
            title="Сохранить результат как",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not output_file:
            return
        
        # Запуск в отдельном потоке
        self.is_processing = True
        self.btn_load.config(state=tk.DISABLED)
        self.btn_clear.config(state=tk.DISABLED)
        self.btn_merge.config(state=tk.DISABLED)
        
        thread = threading.Thread(
            target=self.merge_files,
            args=(output_file,),
            daemon=True
        )
        thread.start()
    
    def merge_files(self, output_file):
        """
        Слияние NDJSON файлов (выполняется в отдельном потоке)
        Построчное чтение - минимальное использование памяти!
        """
        try:
            self.root.after(0, lambda: self.log("Начало слияния файлов...", "info"))
            
            total_files = len(self.files)
            total_lines = 0
            error_count = 0
            
            with open(output_file, 'w', encoding='utf-8') as outfile:
                
                for file_idx, filepath in enumerate(self.files):
                    filename = os.path.basename(filepath)
                    file_lines = 0
                    
                    self.root.after(0, lambda fn=filename, idx=file_idx: 
                        self.log(f"Обработка: {fn} ({idx+1}/{total_files})"))
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as infile:
                            for line in infile:
                                line = line.strip()
                                # Пропускаем пустые строки
                                if line:
                                    outfile.write(line + '\n')
                                    file_lines += 1
                                    total_lines += 1
                        
                        self.root.after(0, lambda fn=filename, fl=file_lines: 
                            self.log(f"  ✓ {fn}: {fl:,} строк"))
                    
                    except Exception as e:
                        error_count += 1
                        self.root.after(0, lambda fn=filename, err=str(e): 
                            self.log(f"❌ Ошибка в файле {fn}: {err}", "error"))
                    
                    # Обновление прогресса
                    progress = ((file_idx + 1) / total_files) * 100
                    self.root.after(0, lambda p=progress, tl=total_lines: 
                        self.update_progress(p, tl))
            
            # Успешное завершение
            output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            output_size_gb = os.path.getsize(output_file) / (1024 * 1024 * 1024)
            
            if output_size_gb >= 1:
                size_str = f"{output_size_gb:.2f} GB"
            else:
                size_str = f"{output_size_mb:.2f} MB"
            
            self.root.after(0, lambda: self.log(
                f"✅ Готово! Файл: {os.path.basename(output_file)}", 
                "success"
            ))
            self.root.after(0, lambda: self.log(
                f"   Размер: {size_str} | Строк: {total_lines:,} | Ошибок: {error_count}", 
                "success"
            ))
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Успех", 
                f"Файлы успешно объединены!\n\n"
                f"Результат: {output_file}\n"
                f"Размер: {size_str}\n"
                f"Всего строк: {total_lines:,}\n"
                f"Ошибок: {error_count}"
            ))
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Критическая ошибка: {str(e)}", "error"))
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        
        finally:
            self.root.after(0, self.finish_processing)
    
    def update_progress(self, percent, total_lines):
        """Обновить прогресс-бар"""
        self.progress_var.set(percent)
        self.progress_label.config(text=f"{percent:.1f}% | Строк: {total_lines:,}")
    
    def finish_processing(self):
        """Завершение обработки"""
        self.is_processing = False
        self.btn_load.config(state=tk.NORMAL)
        self.btn_clear.config(state=tk.NORMAL)
        self.btn_merge.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    app = JSONMergerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()