import os
import shutil
import configparser
from pathlib import Path

#Данный код по путю папки удаляет папки, которые старые(УКАЗАННЫЕ В keep_count или config.ini )
#ЧТОБЫ УДАЛЯТЬ ДРУГОЕ КОЛИЧЕСТВО СТОИТ ПОМЕНЯТЬ В config.ini эту переменную на желаемую (keep_count)


def get_sorted_folders(directory):
    """Получить список папок, отсортированных по дате изменения."""
    folders = [f for f in Path(directory).iterdir() if f.is_dir()]
    folders.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return folders

def cleanup_folders(directory, keep_count):
    """Удалить старые папки, оставив только указанное количество."""
    folders = get_sorted_folders(directory)
    if len(folders) > keep_count:
        for folder in folders[keep_count:]:
            shutil.rmtree(folder)  # Рекурсивное удаление папки со всем содержимым
        return f"Удалено {len(folders) - keep_count} папок."
    return "Удалять ничего не нужно."


def load_config(config_path):
    """Загрузить настройки из файла конфигурации."""
    config = configparser.ConfigParser()
    config.read(config_path)
    return int(config["Settings"]["keep_folders"])

def main():
    # Укажите путь к папке для очистки
    target_directory = r"C:\Users\admin\Desktop\main"

    config_path = "config.ini"
    keep_count = load_config(config_path)

    # keep_count = 5

    # Проверка существования директории
    if not os.path.exists(target_directory):
        print(f"Директория {target_directory} не существует.")
        return

    # Очистка папок
    result = cleanup_folders(target_directory, keep_count)
    print(result)
    print("Работа выполнена.")

if __name__ == "__main__":
    main()
