"""
Скрипт для удаления дубликатов в JSON файлах
Версия: 1.6 — полное удаление "\" и замена внутренних кавычек в title/Наименование

Что делает скрипт:
1. Читает файл построчно.
2. ДО парсинга JSON очищает сырую строку от всех "\" и всех управляющих символов.
3. ДО парсинга заменяет внутренние " в значениях title/Наименование на "-".
4. Парсит JSON.
5. Нормализует title (удаляет пробелы по краям).
6. Удаляет дубликаты.
7. Формирует отчет и итоговые файлы.
"""

# ==================== ИМПОРТ БИБЛИОТЕК ====================

import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox
import json
import threading
import os
import time
import re


# ==================== НАСТРОЙКИ ====================

MAX_LINES_PER_FILE = 3000000  # 3 миллиона строк

NEW_STOCK_VALUE = "188"
NEW_UNDER_ORDER_VALUE = "5-8 дней"
NEW_PRICE_VALUE = "110 руб"


# ==================== ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ ====================

class JSONCleanerApp:
    
    def __init__(self, root):
        self.root = root
        self.root.title("Очистка JSON от дубликатов v1.6")
        self.root.geometry("750x550")
        self.root.resizable(True, True)
        
        # Все управляющие символы: 0x00-0x1F, 0x7F-0x9F
        self.re_control_chars = re.compile(r'[\x00-\x1f\x7f-\x9f]')
        
        # Пробельные символы для strip (включая неразрывные)
        self.whitespace_chars = ' \t\n\r\x0b\x0c\xa0\ufeff'
        
        self.selected_files = []
        self.stop_processing = False
        
        self.create_widgets()
    
    
    def create_widgets(self):
        # ---------- РАМКА ДЛЯ КНОПОК ВВЕРХУ ----------
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X)
        
        self.btn_load = tk.Button(
            top_frame, text="📂 Загрузить файлы (до 10)", command=self.load_files,
            font=("Arial", 12), width=25, height=2
        )
        self.btn_load.pack(side=tk.LEFT, padx=10)
        
        self.btn_process = tk.Button(
            top_frame, text="🔧 Удалить дубликаты", command=self.start_processing,
            font=("Arial", 12), width=25, height=2, state=tk.DISABLED
        )
        self.btn_process.pack(side=tk.LEFT, padx=10)
        
        self.btn_stop = tk.Button(
            top_frame, text="⏹ Остановить", command=self.stop_process,
            font=("Arial", 12), width=15, height=2, state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT, padx=10)
        
        # ---------- СПИСОК ВЫБРАННЫХ ФАЙЛОВ ----------
        files_frame = tk.Frame(self.root, pady=5)
        files_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(files_frame, text="Выбранные файлы:", font=("Arial", 11, "bold")).pack(anchor=tk.W)
        
        list_container = tk.Frame(files_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.files_listbox = tk.Listbox(
            list_container, font=("Consolas", 10), height=3, yscrollcommand=scrollbar.set
        )
        self.files_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.files_listbox.yview)
        
        # ---------- ШКАЛА ПРОГРЕССА ----------
        progress_frame = tk.Frame(self.root, pady=10)
        progress_frame.pack(fill=tk.X, padx=10)
        
        self.label_current_file = tk.Label(progress_frame, text="Ожидание...", font=("Arial", 10))
        self.label_current_file.pack(anchor=tk.W)
        
        tk.Label(progress_frame, text="Прогресс по файлам:", font=("Arial", 9)).pack(anchor=tk.W)
        self.progress_files = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=700, mode='determinate')
        self.progress_files.pack(fill=tk.X, pady=2)
        
        tk.Label(progress_frame, text="Прогресс текущего файла:", font=("Arial", 9)).pack(anchor=tk.W)
        self.progress_current = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=700, mode='determinate')
        self.progress_current.pack(fill=tk.X, pady=2)
        
        # ---------- ОБЛАСТЬ ДЛЯ ЛОГОВ ----------
        log_frame = tk.Frame(self.root, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        tk.Label(log_frame, text="Лог выполнения:", font=("Arial", 11, "bold")).pack(anchor=tk.W)
        
        log_scrollbar = tk.Scrollbar(log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            log_frame, font=("Consolas", 9), height=15, state=tk.DISABLED, yscrollcommand=log_scrollbar.set
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)
    
    
    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    
    def load_files(self):
        files = filedialog.askopenfilenames(
            title="Выберите JSON файлы (до 10 штук)",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")]
        )
        if not files:
            return
        if len(files) > 10:
            messagebox.showwarning("Лимит", "Можно выбрать максимум 10 файлов.\nВыбраны первые 10.")
            files = files[:10]
        
        self.selected_files = list(files)
        self.files_listbox.delete(0, tk.END)
        for file_path in self.selected_files:
            self.files_listbox.insert(tk.END, os.path.basename(file_path))
        self.btn_process.config(state=tk.NORMAL)
        self.log(f"Выбрано файлов: {len(self.selected_files)}")
    
    
    def start_processing(self):
        if not self.selected_files:
            return
        self.stop_processing = False
        self.btn_load.config(state=tk.DISABLED)
        self.btn_process.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.progress_files['value'] = 0
        self.progress_current['value'] = 0
        
        threading.Thread(target=self.process_files, daemon=True).start()
    
    
    def stop_process(self):
        self.stop_processing = True
        self.log("⏹ Остановка...")
    
    
    def process_files(self):
        total_files = len(self.selected_files)
        start_time = time.time()
        self.log("=" * 60)
        self.log(f"🚀 Старт обработки {total_files} файлов...")
        
        for index, file_path in enumerate(self.selected_files):
            if self.stop_processing:
                break
            
            file_name = os.path.basename(file_path)
            self.label_current_file.config(text=f"Файл: {file_name} ({index + 1}/{total_files})")
            self.log(f"\n📄 Файл {index + 1}: {file_name}")
            
            try:
                self.process_single_file(file_path)
            except Exception as e:
                self.log(f"❌ Ошибка: {str(e)}")
            
            self.progress_files['value'] = ((index + 1) / total_files) * 100
            self.root.update_idletasks()
        
        elapsed = time.time() - start_time
        self.log("=" * 60)
        self.log(f"✅ Все завершено за {elapsed:.1f} сек")
        
        self.btn_load.config(state=tk.NORMAL)
        self.btn_process.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.label_current_file.config(text="Готово!")
        
        if not self.stop_processing:
            messagebox.showinfo("Готово", "Обработка завершена!\nПроверьте *_errors.txt")
    
    
    def fix_inner_quotes_in_title(self, line: str) -> str:
        """
        Внутри значения ключа "title" или "Наименование"
        заменяет все кавычки " на дефис -, оставляя внешние кавычки как есть.
        
        Работает на сырой строке до json.loads.
        """
        # Обрабатываем оба ключа
        for key in ('"title"', '"Наименование"'):
            search_pos = 0
            while True:
                idx_key = line.find(key, search_pos)
                if idx_key == -1:
                    break
                
                # Двоеточие после ключа
                idx_colon = line.find(':', idx_key + len(key))
                if idx_colon == -1:
                    break
                
                # Открывающая кавычка значения
                idx_open = line.find('"', idx_colon + 1)
                if idx_open == -1:
                    break
                
                # Ищем закрывающую кавычку значения:
                # та, после которой первый значимый символ — ',', '}' или ']'
                n = len(line)
                i = idx_open + 1
                closing = -1
                while i < n:
                    ch = line[i]
                    if ch == '"':
                        j = i + 1
                        # пропускаем пробелы
                        while j < n and line[j] in ' \t\r\n':
                            j += 1
                        if j >= n:
                            closing = i
                            break
                        if line[j] in ',}]':
                            closing = i
                            break
                        # иначе это внутренняя кавычка, идем дальше
                    i += 1
                
                if closing == -1:
                    # Не нашли корректного конца — не трогаем этот ключ
                    search_pos = idx_key + len(key)
                    continue
                
                # Значение между внешними кавычками
                value = line[idx_open + 1:closing]
                if '"' in value:
                    fixed_value = value.replace('"', '-')
                    line = line[:idx_open + 1] + fixed_value + line[closing:]
                    # Продолжаем поиск после обработанного значения
                    search_pos = idx_open + 1 + len(fixed_value) + 1  # +1 за закрывающую кавычку
                else:
                    search_pos = closing + 1
        
        return line
    
    
    def clean_raw_line(self, line: str) -> str:
        """
        Очищает сырую строку ДО попытки парсинга JSON.
        1) удаляет все управляющие символы (0x00-0x1F, 0x7F-0x9F),
        2) удаляет вообще все символы "\" в любом месте строки,
        3) в значениях title/Наименование внутренние " заменяет на "-".
        """
        # 1. Удаляем все управляющие символы
        line = self.re_control_chars.sub('', line)
        
        # 2. Удаляем все обратные слеши "\"
        line = line.replace('\\', '')
        
        # 3. Чиним внутренние кавычки в значениях title/Наименование
        line = self.fix_inner_quotes_in_title(line)
        
        return line
    
    
    def normalize_title_final(self, title):
        """
        Финальная зачистка title уже после парсинга.
        Удаляет пробелы по краям (включая неразрывные).
        """
        if not isinstance(title, str):
            title = str(title)
        return title.strip(self.whitespace_chars)
    
    
    def process_single_file(self, file_path):
        file_dir = os.path.dirname(file_path)
        file_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
        errors_file = os.path.join(file_dir, f"{file_name_no_ext}_errors.txt")
        
        # Подсчет строк
        self.log("   Подсчёт строк...")
        with open(file_path, 'r', encoding='utf-8') as f_count:
            total_lines = sum(1 for _ in f_count)
        self.log(f"   Строк: {total_lines:,}".replace(',', ' '))
        
        seen_titles = set()
        unique_records = []
        skipped_items = []
        
        empty_lines = 0
        duplicates = 0
        parse_errors = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if self.stop_processing:
                    return
                if line_num % 10000 == 0:
                    self.progress_current['value'] = (line_num / total_lines) * 100
                    self.root.update_idletasks()
                
                original_line = line
                line = line.strip()
                if not line:
                    empty_lines += 1
                    continue
                
                # --- ЭТАП 1: ОЧИСТКА СЫРОЙ СТРОКИ ---
                cleaned_line = self.clean_raw_line(line)
                
                # --- ЭТАП 2: ПАРСИНГ ---
                try:
                    record = json.loads(cleaned_line, strict=False)
                except json.JSONDecodeError as e:
                    parse_errors += 1
                    skipped_items.append({
                        'reason': 'json_error',
                        'line_number': line_num,
                        'content': original_line.strip(),  # сохраняем оригинал в лог
                        'error': str(e)
                    })
                    continue
                
                # --- ЭТАП 3: ПОИСК И НОРМАЛИЗАЦИЯ TITLE ---
                title_field = None
                raw_title = None
                
                if 'title' in record:
                    title_field = 'title'
                    raw_title = record.get('title')
                elif 'Наименование' in record:
                    title_field = 'Наименование'
                    raw_title = record.get('Наименование')
                
                if title_field is not None:
                    clean_title = self.normalize_title_final(raw_title)
                    record[title_field] = clean_title
                    
                    # Проверка уникальности
                    if clean_title in seen_titles:
                        duplicates += 1
                        skipped_items.append({
                            'reason': 'duplicate',
                            'line_number': line_num,
                            'field_name': title_field,
                            'original_title': raw_title,
                            'normalized_title': clean_title,
                            'content': original_line.strip()
                        })
                        continue
                    else:
                        seen_titles.add(clean_title)
                
                # --- ЭТАП 4: ЗАМЕНА ПОЛЕЙ ---
                record = self.replace_field_values(record)
                unique_records.append(record)
        
        self.progress_current['value'] = 100
        self.log(f"   ✓ Пустых: {empty_lines}")
        self.log(f"   ✓ Дубликатов: {duplicates}")
        self.log(f"   ✓ Ок записей: {len(unique_records)}")
        self.log(f"   ⚠️ Ошибок JSON: {parse_errors}")
        
        if skipped_items:
            self.log(f"   ⚠️ В отчете (errors): {len(skipped_items)}")
            self.save_error_lines(skipped_items, errors_file)
        else:
            self.log("   ✓ Ошибок нет")
            
        # Сохранение результата
        if len(unique_records) <= MAX_LINES_PER_FILE:
            out = os.path.join(file_dir, f"{file_name_no_ext}_cleaned.json")
            self.save_records(unique_records, out)
            self.log(f"   💾 {os.path.basename(out)}")
        else:
            self.log("   📦 Разбивка на части...")
            part = 1
            for i in range(0, len(unique_records), MAX_LINES_PER_FILE):
                chunk = unique_records[i:i + MAX_LINES_PER_FILE]
                out = os.path.join(file_dir, f"{file_name_no_ext}_cleaned_part{part}.json")
                self.save_records(chunk, out)
                self.log(f"   💾 Часть {part}: {len(chunk)} записей")
                part += 1
    
    
    def replace_field_values(self, record):
        if 'stock' in record:
            record['stock'] = NEW_STOCK_VALUE
        if 'Склад' in record:
            record['Склад'] = NEW_STOCK_VALUE
        
        if 'under_order' in record:
            record['under_order'] = NEW_UNDER_ORDER_VALUE
        if 'under-order' in record:
            record['under-order'] = NEW_UNDER_ORDER_VALUE
        if 'Под заказ' in record:
            record['Под заказ'] = NEW_UNDER_ORDER_VALUE
        
        if 'price' in record:
            record['price'] = NEW_PRICE_VALUE
        if 'Цена' in record:
            record['Цена'] = NEW_PRICE_VALUE
        return record
    
    
    def save_records(self, records, path):
        with open(path, 'w', encoding='utf-8') as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    
    
    def save_error_lines(self, items, path):
        js_err = [x for x in items if x['reason'] == 'json_error']
        dups = [x for x in items if x['reason'] == 'duplicate']
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"ОТЧЕТ ОБ ОШИБКАХ\nВсего: {len(items)}\nJSON Errors: {len(js_err)}\nДубликаты: {len(dups)}\n\n")
            
            if js_err:
                f.write("=== ОШИБКИ JSON (Символы или формат) ===\n")
                for i in js_err:
                    f.write(f"Стр {i['line_number']}: {i['error']}\nContent: {i['content']}\n\n")
            
            if dups:
                f.write("=== ДУБЛИКАТЫ ===\n")
                for i in dups:
                    f.write(f"Стр {i['line_number']} ({i['field_name']})\nTitle: '{i['normalized_title']}'\n\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = JSONCleanerApp(root)
    root.mainloop()