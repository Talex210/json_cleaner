"""
Скрипт для удаления дубликатов в JSON файлах
Версия: 1.2 — нормализация title и расширенный отчёт

Что делает скрипт:
1. Открывает окно для выбора JSON файла (или нескольких файлов)
2. Удаляет пустые строки
3. Очищает значения полей "title" / "Наименование" и удаляет дубликаты по ним
4. Заменяет значения полей stock/Склад, under_order/Под заказ, price/Цена
5. Разбивает большие файлы на части по 3 000 000 строк
6. Сохраняет в отчёт строки, которые не попали в итоговый файл
7. Сохраняет результат в той же папке
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


# ==================== НАСТРОЙКИ ====================

# Максимальное количество строк в одном файле
MAX_LINES_PER_FILE = 3000000  # 3 миллиона строк

# Значения для замены полей
NEW_STOCK_VALUE = "188"
NEW_UNDER_ORDER_VALUE = "5-8 дней"
NEW_PRICE_VALUE = "110 руб"

# Символы, которые нужно вырезать из title / Наименование
#   пробелы по краям удаляются через .strip()
#   внутри строки удаляются: "\" и управляющие символы 0x02, 0x01, 0x17, 0x03, 0x04, 0x1F
BAD_TITLE_CHARS = '\\\x02\x01\x17\x03\x04\x1f'
TITLE_TRANSLATION_TABLE = str.maketrans('', '', BAD_TITLE_CHARS)


# ==================== ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ ====================

class JSONCleanerApp:
    """
    Главный класс приложения.
    """
    
    def __init__(self, root):
        """
        Инициализация приложения.
        """
        self.root = root
        self.root.title("Очистка JSON от дубликатов v1.2")
        self.root.geometry("750x550")
        self.root.resizable(True, True)
        
        self.selected_files = []
        self.stop_processing = False
        
        self.create_widgets()
    
    
    def create_widgets(self):
        """
        Создание всех элементов интерфейса.
        """
        
        # ---------- РАМКА ДЛЯ КНОПОК ВВЕРХУ ----------
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X)
        
        self.btn_load = tk.Button(
            top_frame,
            text="📂 Загрузить файлы (до 10)",
            command=self.load_files,
            font=("Arial", 12),
            width=25,
            height=2
        )
        self.btn_load.pack(side=tk.LEFT, padx=10)
        
        self.btn_process = tk.Button(
            top_frame,
            text="🔧 Удалить дубликаты",
            command=self.start_processing,
            font=("Arial", 12),
            width=25,
            height=2,
            state=tk.DISABLED
        )
        self.btn_process.pack(side=tk.LEFT, padx=10)
        
        self.btn_stop = tk.Button(
            top_frame,
            text="⏹ Остановить",
            command=self.stop_process,
            font=("Arial", 12),
            width=15,
            height=2,
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT, padx=10)
        
        # ---------- СПИСОК ВЫБРАННЫХ ФАЙЛОВ ----------
        files_frame = tk.Frame(self.root, pady=5)
        files_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(
            files_frame, 
            text="Выбранные файлы:", 
            font=("Arial", 11, "bold")
        ).pack(anchor=tk.W)
        
        list_container = tk.Frame(files_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Уменьшили высоту в два раза (было 6 -> стало 3)
        self.files_listbox = tk.Listbox(
            list_container,
            font=("Consolas", 10),
            height=3,
            yscrollcommand=scrollbar.set
        )
        self.files_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.files_listbox.yview)
        
        # ---------- ШКАЛА ПРОГРЕССА ----------
        progress_frame = tk.Frame(self.root, pady=10)
        progress_frame.pack(fill=tk.X, padx=10)
        
        self.label_current_file = tk.Label(
            progress_frame,
            text="Ожидание...",
            font=("Arial", 10)
        )
        self.label_current_file.pack(anchor=tk.W)
        
        tk.Label(
            progress_frame, 
            text="Прогресс по файлам:", 
            font=("Arial", 9)
        ).pack(anchor=tk.W)
        
        self.progress_files = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            length=700,
            mode='determinate'
        )
        self.progress_files.pack(fill=tk.X, pady=2)
        
        tk.Label(
            progress_frame, 
            text="Прогресс текущего файла:", 
            font=("Arial", 9)
        ).pack(anchor=tk.W)
        
        self.progress_current = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            length=700,
            mode='determinate'
        )
        self.progress_current.pack(fill=tk.X, pady=2)
        
        # ---------- ОБЛАСТЬ ДЛЯ ЛОГОВ ----------
        log_frame = tk.Frame(self.root, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        tk.Label(
            log_frame, 
            text="Лог выполнения:", 
            font=("Arial", 11, "bold")
        ).pack(anchor=tk.W)
        
        log_scrollbar = tk.Scrollbar(log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Увеличили высоту (было 10 -> стало 15)
        self.log_text = tk.Text(
            log_frame,
            font=("Consolas", 9),
            height=15,
            state=tk.DISABLED,
            yscrollcommand=log_scrollbar.set
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)
    
    
    def log(self, message):
        """
        Добавляет сообщение в лог.
        """
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    
    def load_files(self):
        """
        Открывает диалог выбора файлов.
        """
        files = filedialog.askopenfilenames(
            title="Выберите JSON файлы (до 10 штук)",
            filetypes=[
                ("JSON файлы", "*.json"),
                ("Все файлы", "*.*")
            ]
        )
        
        if not files:
            return
        
        if len(files) > 10:
            messagebox.showwarning(
                "Слишком много файлов",
                "Можно выбрать максимум 10 файлов.\nВыбраны первые 10."
            )
            files = files[:10]
        
        self.selected_files = list(files)
        
        self.files_listbox.delete(0, tk.END)
        
        for file_path in self.selected_files:
            file_name = os.path.basename(file_path)
            self.files_listbox.insert(tk.END, file_name)
        
        self.btn_process.config(state=tk.NORMAL)
        
        self.log(f"Выбрано файлов: {len(self.selected_files)}")
    
    
    def start_processing(self):
        """
        Запускает обработку файлов в отдельном потоке.
        """
        if not self.selected_files:
            messagebox.showwarning("Нет файлов", "Сначала выберите файлы для обработки!")
            return
        
        self.stop_processing = False
        
        self.btn_load.config(state=tk.DISABLED)
        self.btn_process.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        self.progress_files['value'] = 0
        self.progress_current['value'] = 0
        
        processing_thread = threading.Thread(target=self.process_files)
        processing_thread.daemon = True
        processing_thread.start()
    
    
    def stop_process(self):
        """
        Останавливает обработку файлов.
        """
        self.stop_processing = True
        self.log("⏹ Остановка обработки... Дождитесь завершения текущего файла.")
    
    
    def process_files(self):
        """
        Основная функция обработки всех выбранных файлов.
        """
        total_files = len(self.selected_files)
        start_time = time.time()
        
        self.log("=" * 60)
        self.log(f"🚀 Начинаем обработку {total_files} файлов...")
        self.log("=" * 60)
        
        for index, file_path in enumerate(self.selected_files):
            if self.stop_processing:
                self.log("❌ Обработка остановлена пользователем")
                break
            
            file_name = os.path.basename(file_path)
            self.label_current_file.config(
                text=f"Обрабатывается: {file_name} ({index + 1}/{total_files})"
            )
            
            self.log(f"\n📄 Файл {index + 1}/{total_files}: {file_name}")
            
            try:
                self.process_single_file(file_path)
            except Exception as e:
                self.log(f"❌ Ошибка при обработке файла: {str(e)}")
            
            progress_percent = ((index + 1) / total_files) * 100
            self.progress_files['value'] = progress_percent
            self.root.update_idletasks()
        
        elapsed_time = time.time() - start_time
        self.log("=" * 60)
        self.log(f"✅ Обработка завершена за {elapsed_time:.1f} секунд")
        self.log("=" * 60)
        
        self.btn_load.config(state=tk.NORMAL)
        self.btn_process.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.label_current_file.config(text="Готово!")
        
        if not self.stop_processing:
            messagebox.showinfo(
                "Готово!", 
                f"Обработка {total_files} файлов завершена!\n"
                f"Время: {elapsed_time:.1f} секунд\n\n"
                f"Проверьте файлы *_errors.txt для просмотра\n"
                f"строк, не попавших в итоговый файл (если они есть)."
            )
    
    
    def normalize_title(self, title):
        """
        Очищает значение title / Наименование:
        - обрезает пробелы по краям;
        - удаляет все "\" и управляющие символы 0x02,0x01,0x17,0x03,0x04,0x1F.
        """
        if title is None:
            return None
        if not isinstance(title, str):
            title = str(title)
        # Сначала обрезаем пробелы, потом удаляем лишние символы и ещё раз обрезаем
        cleaned = title.strip().translate(TITLE_TRANSLATION_TABLE).strip()
        return cleaned
    
    
    def process_single_file(self, file_path):
        """
        Обрабатывает один JSON файл.
        """
        
        file_name = os.path.basename(file_path)
        file_dir = os.path.dirname(file_path)
        file_name_without_ext = os.path.splitext(file_name)[0]
        
        # Путь к файлу с отчётом по пропущенным строкам
        errors_file_path = os.path.join(file_dir, f"{file_name_without_ext}_errors.txt")
        
        # ШАГ 1: Подсчитываем количество строк
        self.log("   Подсчёт строк в файле...")
        self.progress_current['value'] = 0
        self.root.update_idletasks()
        
        total_lines = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for _ in f:
                total_lines += 1
        
        self.log(f"   Всего строк в файле: {total_lines:,}".replace(',', ' '))
        
        # ШАГ 2: Читаем и обрабатываем файл
        self.log("   Чтение и обработка данных...")
        
        seen_titles = set()
        unique_records = []
        
        # Список для строк, не попавших в итоговый файл
        skipped_items = []
        
        # Счётчики
        empty_lines = 0
        duplicates = 0
        parse_errors = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                if self.stop_processing:
                    return
                
                # Обновляем прогресс каждые 10000 строк
                if line_number % 10000 == 0:
                    progress_percent = (line_number / total_lines) * 100
                    self.progress_current['value'] = progress_percent
                    self.root.update_idletasks()
                
                # Сохраняем оригинальную строку для отчёта
                original_line = line
                
                # Убираем пробелы и переносы
                line = line.strip()
                
                # Пропускаем пустые строки
                if not line:
                    empty_lines += 1
                    continue
                
                # Пытаемся распарсить JSON
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    parse_errors += 1
                    skipped_items.append({
                        'reason': 'json_error',
                        'line_number': line_number,
                        'content': original_line.strip(),
                        'error': str(e)
                    })
                    continue
                
                # Получаем значение title или Наименование
                title_field = None
                raw_title = None
                normalized_title = None
                
                if 'title' in record:
                    title_field = 'title'
                    raw_title = record.get('title')
                elif 'Наименование' in record:
                    title_field = 'Наименование'
                    raw_title = record.get('Наименование')
                
                # Если есть одно из полей — очищаем и проверяем на дубликат
                if title_field is not None:
                    normalized_title = self.normalize_title(raw_title)
                    # Записываем очищенное значение обратно в запись
                    record[title_field] = normalized_title
                    
                    # Уникальность обеспечиваем по очищенному значению
                    if normalized_title is not None:
                        if normalized_title in seen_titles:
                            duplicates += 1
                            skipped_items.append({
                                'reason': 'duplicate',
                                'line_number': line_number,
                                'field_name': title_field,
                                'original_title': raw_title,
                                'normalized_title': normalized_title,
                                'content': original_line.strip()
                            })
                            continue
                        else:
                            seen_titles.add(normalized_title)
                
                # Заменяем значения полей stock / under_order / price
                record = self.replace_field_values(record)
                
                unique_records.append(record)
        
        # Обновляем прогресс на 100%
        self.progress_current['value'] = 100
        self.root.update_idletasks()
        
        # Выводим статистику
        self.log(f"   ✓ Пустых строк удалено: {empty_lines:,}".replace(',', ' '))
        self.log(f"   ✓ Дубликатов удалено: {duplicates:,}".replace(',', ' '))
        self.log(f"   ✓ Уникальных записей: {len(unique_records):,}".replace(',', ' '))
        self.log(f"   ⚠️ Строк с ошибкой JSON: {parse_errors:,}".replace(',', ' '))
        
        # ШАГ 3: Сохраняем отчёт по строкам, не попавшим в итоговый файл
        if skipped_items:
            self.log(
                f"   ⚠️ Строк, не попавших в итоговый файл: "
                f"{len(skipped_items):,}".replace(',', ' ')
            )
            self.save_error_lines(skipped_items, errors_file_path)
            self.log(f"   📝 Отчёт сохранён в: {os.path.basename(errors_file_path)}")
        else:
            self.log(f"   ✓ Все распознанные строки попали в итоговый файл")
        
        # ШАГ 4: Сохраняем результат
        self.log("   Сохранение результата...")
        
        if len(unique_records) <= MAX_LINES_PER_FILE:
            output_file = os.path.join(file_dir, f"{file_name_without_ext}_cleaned.json")
            self.save_records_to_file(unique_records, output_file)
            self.log(f"   ✓ Сохранено в: {os.path.basename(output_file)}")
        else:
            self.log(
                f"   📦 Разбиваем на части по {MAX_LINES_PER_FILE:,} строк..."
                .replace(',', ' ')
            )
            
            part_number = 1
            for i in range(0, len(unique_records), MAX_LINES_PER_FILE):
                chunk = unique_records[i:i + MAX_LINES_PER_FILE]
                output_file = os.path.join(
                    file_dir, 
                    f"{file_name_without_ext}_cleaned_part{part_number}.json"
                )
                self.save_records_to_file(chunk, output_file)
                self.log(
                    f"   ✓ Часть {part_number}: {len(chunk):,} записей"
                    .replace(',', ' ')
                )
                part_number += 1
        
        self.log(f"   ✅ Файл обработан успешно!")
    
    
    def save_error_lines(self, skipped_items, output_file):
        """
        Сохраняет в текстовый файл строки, которые не попали в итоговый JSON.
        
        skipped_items — список словарей с ключами:
            reason: 'json_error' или 'duplicate'
            line_number: номер строки в исходном файле
            content: исходный текст строки
            ...
        """
        json_errors = [x for x in skipped_items if x['reason'] == 'json_error']
        duplicates = [x for x in skipped_items if x['reason'] == 'duplicate']
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ОТЧЁТ О СТРОКАХ, НЕ ПОПАВШИХ В ИТОГОВЫЙ ФАЙЛ\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Всего пропущенных строк: {len(skipped_items)}\n")
            f.write(f"  - ошибок JSON:      {len(json_errors)}\n")
            f.write(f"  - дубликатов title: {len(duplicates)}\n\n")
            f.write("Ниже перечислены строки, которые НЕ были записаны в итоговый файл.\n\n")
            
            if json_errors:
                f.write("=" * 80 + "\n")
                f.write("РАЗДЕЛ 1. Строки с ошибкой JSON\n")
                f.write("=" * 80 + "\n\n")
                for item in json_errors:
                    f.write(f"Строка #{item['line_number']} (ошибка JSON):\n")
                    f.write(f"Содержимое: {item['content']}\n")
                    f.write(f"Ошибка: {item['error']}\n")
                    f.write("\n" + "-" * 40 + "\n\n")
            
            if duplicates:
                f.write("=" * 80 + "\n")
                f.write("РАЗДЕЛ 2. Дубликаты по title / Наименование\n")
                f.write("=" * 80 + "\n\n")
                for item in duplicates:
                    f.write(
                        f"Строка #{item['line_number']} "
                        f"(дубликат по полю \"{item['field_name']}\"):\n"
                    )
                    f.write(f"Изначальное значение: {repr(item['original_title'])}\n")
                    f.write(f"После очистки:        {repr(item['normalized_title'])}\n")
                    f.write(f"Содержимое: {item['content']}\n")
                    f.write("\n" + "-" * 40 + "\n\n")
    
    
    def replace_field_values(self, record):
        """
        Заменяет значения полей stock, under_order, price на новые.
        """
        
        # Замена поля stock / Склад
        if 'stock' in record:
            record['stock'] = NEW_STOCK_VALUE
        if 'Склад' in record:
            record['Склад'] = NEW_STOCK_VALUE
        
        # Замена поля under_order / under-order / Под заказ
        if 'under_order' in record:
            record['under_order'] = NEW_UNDER_ORDER_VALUE
        if 'under-order' in record:
            record['under-order'] = NEW_UNDER_ORDER_VALUE
        if 'Под заказ' in record:
            record['Под заказ'] = NEW_UNDER_ORDER_VALUE
        
        # Замена поля price / Цена
        if 'price' in record:
            record['price'] = NEW_PRICE_VALUE
        if 'Цена' in record:
            record['Цена'] = NEW_PRICE_VALUE
        
        return record
    
    
    def save_records_to_file(self, records, output_file):
        """
        Сохраняет список записей в JSON файл.
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            for record in records:
                json_line = json.dumps(record, ensure_ascii=False)
                f.write(json_line + '\n')


# ==================== ЗАПУСК ПРОГРАММЫ ====================

if __name__ == "__main__":
    root = tk.Tk()
    app = JSONCleanerApp(root)
    root.mainloop()