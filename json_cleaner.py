"""
Скрипт для удаления дубликатов в JSON файлах
Автор: Assistant
Версия: 1.0

Что делает скрипт:
1. Открывает окно для выбора JSON файла (или нескольких файлов)
2. Удаляет пустые строки
3. Удаляет дубликаты по полю "title" или "Наименование"
4. Заменяет значения полей stock/Склад, under_order/Под заказ, price/Цена
5. Разбивает большие файлы на части по 3 000 000 строк
6. Сохраняет результат в той же папке
"""

# ==================== ИМПОРТ БИБЛИОТЕК ====================
# Это как "подключение инструментов" которые нам понадобятся

import tkinter as tk                    # Библиотека для создания окон и кнопок
from tkinter import filedialog          # Для окна выбора файлов
from tkinter import ttk                 # Для красивой шкалы прогресса
from tkinter import messagebox          # Для всплывающих сообщений
import json                             # Для работы с JSON файлами
import threading                        # Для работы в нескольких потоках (чтобы окно не зависало)
import os                               # Для работы с файлами и папками
import time                             # Для измерения времени работы


# ==================== НАСТРОЙКИ ====================
# Здесь можно менять значения для замены полей

# Максимальное количество строк в одном файле
MAX_LINES_PER_FILE = 3000000  # 3 миллиона строк

# Значения для замены полей
NEW_STOCK_VALUE = "188"           # Новое значение для поля "stock" или "Склад"
NEW_UNDER_ORDER_VALUE = "5-8 дней"  # Новое значение для поля "under_order" или "Под заказ"
NEW_PRICE_VALUE = "110 руб"       # Новое значение для поля "price" или "Цена"


# ==================== ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ ====================
# Класс — это как "чертёж" нашей программы, в котором описано всё, что она умеет делать

class JSONCleanerApp:
    """
    Главный класс приложения.
    Создаёт окно с кнопками и управляет всей работой программы.
    """
    
    def __init__(self, root):
        """
        Инициализация — это то, что происходит при запуске программы.
        root — это главное окно программы.
        """
        self.root = root  # Сохраняем ссылку на главное окно
        self.root.title("Очистка JSON от дубликатов")  # Заголовок окна
        self.root.geometry("700x500")  # Размер окна: ширина x высота
        self.root.resizable(True, True)  # Можно ли менять размер окна
        
        # Список выбранных файлов (пока пустой)
        self.selected_files = []
        
        # Флаг для остановки обработки
        self.stop_processing = False
        
        # Создаём все элементы интерфейса
        self.create_widgets()
    
    
    def create_widgets(self):
        """
        Создание всех элементов интерфейса: кнопок, надписей, шкалы прогресса.
        """
        
        # ---------- РАМКА ДЛЯ КНОПОК ВВЕРХУ ----------
        # Frame — это как "контейнер" для группировки элементов
        top_frame = tk.Frame(self.root, pady=10)  # pady — отступ сверху и снизу
        top_frame.pack(fill=tk.X)  # pack — размещаем на окне, fill=X — растянуть по ширине
        
        # Кнопка "Загрузить файлы"
        self.btn_load = tk.Button(
            top_frame,                          # В какой рамке разместить
            text="📂 Загрузить файлы (до 10)",  # Текст на кнопке
            command=self.load_files,            # Какую функцию вызвать при нажатии
            font=("Arial", 12),                 # Шрифт и размер
            width=25,                           # Ширина кнопки
            height=2                            # Высота кнопки
        )
        self.btn_load.pack(side=tk.LEFT, padx=10)  # Разместить слева с отступом
        
        # Кнопка "Удалить дубликаты"
        self.btn_process = tk.Button(
            top_frame,
            text="🔧 Удалить дубликаты",
            command=self.start_processing,
            font=("Arial", 12),
            width=25,
            height=2,
            state=tk.DISABLED  # Кнопка неактивна, пока не выбраны файлы
        )
        self.btn_process.pack(side=tk.LEFT, padx=10)
        
        # Кнопка "Остановить"
        self.btn_stop = tk.Button(
            top_frame,
            text="⏹ Остановить",
            command=self.stop_process,
            font=("Arial", 12),
            width=15,
            height=2,
            state=tk.DISABLED  # Неактивна, пока обработка не идёт
        )
        self.btn_stop.pack(side=tk.LEFT, padx=10)
        
        # ---------- СПИСОК ВЫБРАННЫХ ФАЙЛОВ ----------
        files_frame = tk.Frame(self.root, pady=5)
        files_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Заголовок списка
        tk.Label(
            files_frame, 
            text="Выбранные файлы:", 
            font=("Arial", 11, "bold")
        ).pack(anchor=tk.W)  # anchor=W — прижать к левому краю (West)
        
        # Список файлов с прокруткой
        list_container = tk.Frame(files_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # Полоса прокрутки
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Сам список (Listbox)
        self.files_listbox = tk.Listbox(
            list_container,
            font=("Consolas", 10),
            height=8,
            yscrollcommand=scrollbar.set  # Связываем с прокруткой
        )
        self.files_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.files_listbox.yview)
        
        # ---------- ШКАЛА ПРОГРЕССА ----------
        progress_frame = tk.Frame(self.root, pady=10)
        progress_frame.pack(fill=tk.X, padx=10)
        
        # Надпись над шкалой прогресса (для текущего файла)
        self.label_current_file = tk.Label(
            progress_frame,
            text="Ожидание...",
            font=("Arial", 10)
        )
        self.label_current_file.pack(anchor=tk.W)
        
        # Шкала прогресса для файлов
        tk.Label(
            progress_frame, 
            text="Прогресс по файлам:", 
            font=("Arial", 9)
        ).pack(anchor=tk.W)
        
        self.progress_files = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,  # Горизонтальная шкала
            length=650,            # Длина шкалы
            mode='determinate'     # Режим с конкретным прогрессом (0-100%)
        )
        self.progress_files.pack(fill=tk.X, pady=2)
        
        # Шкала прогресса для текущего файла
        tk.Label(
            progress_frame, 
            text="Прогресс текущего файла:", 
            font=("Arial", 9)
        ).pack(anchor=tk.W)
        
        self.progress_current = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            length=650,
            mode='determinate'
        )
        self.progress_current.pack(fill=tk.X, pady=2)
        
        # ---------- ОБЛАСТЬ ДЛЯ ЛОГОВ (СООБЩЕНИЙ) ----------
        log_frame = tk.Frame(self.root, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        tk.Label(
            log_frame, 
            text="Лог выполнения:", 
            font=("Arial", 11, "bold")
        ).pack(anchor=tk.W)
        
        # Полоса прокрутки для лога
        log_scrollbar = tk.Scrollbar(log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Текстовое поле для лога
        self.log_text = tk.Text(
            log_frame,
            font=("Consolas", 9),
            height=8,
            state=tk.DISABLED,  # Нельзя редактировать вручную
            yscrollcommand=log_scrollbar.set
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)
    
    
    def log(self, message):
        """
        Добавляет сообщение в лог (текстовое поле внизу окна).
        """
        self.log_text.config(state=tk.NORMAL)  # Разрешаем редактирование
        self.log_text.insert(tk.END, message + "\n")  # Добавляем текст в конец
        self.log_text.see(tk.END)  # Прокручиваем к концу
        self.log_text.config(state=tk.DISABLED)  # Запрещаем редактирование
    
    
    def load_files(self):
        """
        Открывает диалог выбора файлов.
        Позволяет выбрать до 10 JSON файлов.
        """
        # Открываем диалог выбора файлов
        files = filedialog.askopenfilenames(
            title="Выберите JSON файлы (до 10 штук)",
            filetypes=[
                ("JSON файлы", "*.json"),
                ("Все файлы", "*.*")
            ]
        )
        
        # Если пользователь нажал "Отмена", files будет пустым
        if not files:
            return
        
        # Проверяем, что выбрано не более 10 файлов
        if len(files) > 10:
            messagebox.showwarning(
                "Слишком много файлов",
                "Можно выбрать максимум 10 файлов.\nВыбраны первые 10."
            )
            files = files[:10]  # Берём только первые 10
        
        # Сохраняем список файлов
        self.selected_files = list(files)
        
        # Очищаем список в интерфейсе
        self.files_listbox.delete(0, tk.END)
        
        # Добавляем файлы в список
        for file_path in self.selected_files:
            # Получаем только имя файла (без полного пути)
            file_name = os.path.basename(file_path)
            self.files_listbox.insert(tk.END, file_name)
        
        # Активируем кнопку обработки
        self.btn_process.config(state=tk.NORMAL)
        
        # Сообщение в лог
        self.log(f"Выбрано файлов: {len(self.selected_files)}")
    
    
    def start_processing(self):
        """
        Запускает обработку файлов в отдельном потоке.
        Отдельный поток нужен, чтобы окно не зависало во время работы.
        """
        if not self.selected_files:
            messagebox.showwarning("Нет файлов", "Сначала выберите файлы для обработки!")
            return
        
        # Сбрасываем флаг остановки
        self.stop_processing = False
        
        # Блокируем кнопки во время обработки
        self.btn_load.config(state=tk.DISABLED)
        self.btn_process.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        # Сбрасываем прогресс
        self.progress_files['value'] = 0
        self.progress_current['value'] = 0
        
        # Запускаем обработку в отдельном потоке
        # threading.Thread создаёт новый поток выполнения
        processing_thread = threading.Thread(target=self.process_files)
        processing_thread.daemon = True  # Поток завершится при закрытии программы
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
        Выполняется в отдельном потоке.
        """
        total_files = len(self.selected_files)
        start_time = time.time()
        
        self.log("=" * 50)
        self.log(f"🚀 Начинаем обработку {total_files} файлов...")
        self.log("=" * 50)
        
        for index, file_path in enumerate(self.selected_files):
            # Проверяем, не нажата ли кнопка "Остановить"
            if self.stop_processing:
                self.log("❌ Обработка остановлена пользователем")
                break
            
            # Обновляем надпись текущего файла
            file_name = os.path.basename(file_path)
            self.label_current_file.config(
                text=f"Обрабатывается: {file_name} ({index + 1}/{total_files})"
            )
            
            self.log(f"\n📄 Файл {index + 1}/{total_files}: {file_name}")
            
            try:
                # Обрабатываем файл
                self.process_single_file(file_path)
            except Exception as e:
                self.log(f"❌ Ошибка при обработке файла: {str(e)}")
            
            # Обновляем прогресс по файлам
            progress_percent = ((index + 1) / total_files) * 100
            self.progress_files['value'] = progress_percent
            self.root.update_idletasks()  # Обновляем интерфейс
        
        # Обработка завершена
        elapsed_time = time.time() - start_time
        self.log("=" * 50)
        self.log(f"✅ Обработка завершена за {elapsed_time:.1f} секунд")
        self.log("=" * 50)
        
        # Разблокируем кнопки
        self.btn_load.config(state=tk.NORMAL)
        self.btn_process.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.label_current_file.config(text="Готово!")
        
        # Показываем сообщение об успешном завершении
        if not self.stop_processing:
            messagebox.showinfo(
                "Готово!", 
                f"Обработка {total_files} файлов завершена!\n"
                f"Время: {elapsed_time:.1f} секунд"
            )
    
    
    def process_single_file(self, file_path):
        """
        Обрабатывает один JSON файл.
        
        Шаги:
        1. Читаем файл построчно
        2. Пропускаем пустые строки
        3. Парсим JSON
        4. Проверяем на дубликаты по title/Наименование
        5. Заменяем значения полей
        6. Если строк больше 3 000 000 — разбиваем на несколько файлов
        7. Сохраняем результат
        """
        
        file_name = os.path.basename(file_path)
        file_dir = os.path.dirname(file_path)
        file_name_without_ext = os.path.splitext(file_name)[0]
        
        # ШАГ 1: Подсчитываем количество строк в файле
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
        
        # Множество (set) для хранения уже встреченных значений title
        # Множество позволяет быстро проверять, есть ли уже такое значение
        seen_titles = set()
        
        # Список для хранения уникальных записей
        unique_records = []
        
        # Счётчики для статистики
        empty_lines = 0
        duplicates = 0
        processed_lines = 0
        parse_errors = 0
        
        # Открываем файл для чтения
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                # Проверяем, не остановлена ли обработка
                if self.stop_processing:
                    return
                
                # Обновляем прогресс каждые 10000 строк
                if line_number % 10000 == 0:
                    progress_percent = (line_number / total_lines) * 100
                    self.progress_current['value'] = progress_percent
                    self.root.update_idletasks()
                
                # Убираем пробелы и переносы строк в начале и конце
                line = line.strip()
                
                # Пропускаем пустые строки
                if not line:
                    empty_lines += 1
                    continue
                
                # Пытаемся распарсить JSON
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    # Если строка — не валидный JSON, пропускаем её
                    parse_errors += 1
                    continue
                
                # Получаем значение title или Наименование
                title = None
                if 'title' in record:
                    title = record.get('title')
                elif 'Наименование' in record:
                    title = record.get('Наименование')
                
                # Если title есть и уже был — это дубликат
                if title is not None:
                    if title in seen_titles:
                        duplicates += 1
                        continue  # Пропускаем дубликат
                    else:
                        seen_titles.add(title)  # Добавляем в множество
                
                # Заменяем значения полей
                record = self.replace_field_values(record)
                
                # Добавляем запись в список уникальных
                unique_records.append(record)
                processed_lines += 1
        
        # Обновляем прогресс на 100%
        self.progress_current['value'] = 100
        self.root.update_idletasks()
        
        # Выводим статистику
        self.log(f"   ✓ Пустых строк удалено: {empty_lines:,}".replace(',', ' '))
        self.log(f"   ✓ Дубликатов удалено: {duplicates:,}".replace(',', ' '))
        self.log(f"   ✓ Ошибок парсинга: {parse_errors:,}".replace(',', ' '))
        self.log(f"   ✓ Уникальных записей: {len(unique_records):,}".replace(',', ' '))
        
        # ШАГ 3: Сохраняем результат
        self.log("   Сохранение результата...")
        
        if len(unique_records) <= MAX_LINES_PER_FILE:
            # Если записей меньше или равно 3 миллиона — сохраняем в один файл
            output_file = os.path.join(file_dir, f"{file_name_without_ext}_cleaned.json")
            self.save_records_to_file(unique_records, output_file)
            self.log(f"   ✓ Сохранено в: {os.path.basename(output_file)}")
        else:
            # Если записей больше 3 миллионов — разбиваем на части
            self.log(f"   📦 Разбиваем на части по {MAX_LINES_PER_FILE:,} строк...".replace(',', ' '))
            
            part_number = 1
            for i in range(0, len(unique_records), MAX_LINES_PER_FILE):
                chunk = unique_records[i:i + MAX_LINES_PER_FILE]
                output_file = os.path.join(
                    file_dir, 
                    f"{file_name_without_ext}_cleaned_part{part_number}.json"
                )
                self.save_records_to_file(chunk, output_file)
                self.log(f"   ✓ Часть {part_number}: {len(chunk):,} записей → {os.path.basename(output_file)}".replace(',', ' '))
                part_number += 1
        
        self.log(f"   ✅ Файл обработан успешно!")
    
    
    def replace_field_values(self, record):
        """
        Заменяет значения полей stock, under_order, price на новые.
        Также обрабатывает русские названия полей.
        
        record — это словарь (одна запись из JSON)
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
        Сохраняет список записей в JSON файл (по одной записи на строку).
        
        records — список словарей
        output_file — путь к файлу для сохранения
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            for record in records:
                # Записываем каждую запись в отдельную строку
                # ensure_ascii=False — чтобы русские буквы сохранялись как есть
                json_line = json.dumps(record, ensure_ascii=False)
                f.write(json_line + '\n')


# ==================== ЗАПУСК ПРОГРАММЫ ====================

if __name__ == "__main__":
    """
    Эта часть кода выполняется только если файл запущен напрямую
    (а не импортирован как модуль в другую программу).
    """
    
    # Создаём главное окно
    root = tk.Tk()
    
    # Создаём наше приложение
    app = JSONCleanerApp(root)
    
    # Запускаем главный цикл обработки событий
    # (программа будет работать, пока окно не закроют)
    root.mainloop()