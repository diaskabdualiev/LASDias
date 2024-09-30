import requests
import os

# URL для получения списка приложений в формате JSON
json_url = "https://store.anyapp.tech/liappstore/apps_prod.json"
apk_base_url = "https://store.anyapp.tech/liappstore/apps/"
apk_directory = "apks"
version_file = "installed_versions.txt"

# Создаем директорию для сохранения APK, если она не существует
if not os.path.exists(apk_directory):
    os.makedirs(apk_directory)

# Получаем список файлов, которые уже установлены в папке 'apks'
def get_installed_files():
    return {f for f in os.listdir(apk_directory) if os.path.isfile(os.path.join(apk_directory, f))}

# Получаем список файлов из JSON с информацией о версиях
def get_json_files():
    response = requests.get(json_url)
    apps_list = response.json()
    return {app["filename"]: (app["version"], app["adaptation"]) for app in apps_list}

# Проверяем, какие файлы нужно обновить, а какие уже установлены
def compare_files(installed_files, json_files):
    to_update = {}
    no_update_needed = {}

    for filename, (version, adaptation) in json_files.items():
        if filename in installed_files:
            no_update_needed[filename] = (version, adaptation)  # Уже установлено, обновление не нужно
        else:
            to_update[filename] = (version, adaptation)  # Нужно обновить

    return to_update, no_update_needed

# Функция для загрузки файла с прогрессом
def download_file_with_progress(url, dest_path):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024  # Размер блока для чтения данных

    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)

    with open(dest_path, 'wb') as apk_file:
        for data in response.iter_content(block_size):
            apk_file.write(data)
            progress_bar.update(len(data))

    progress_bar.close()

    if total_size != 0 and progress_bar.n != total_size:
        print("Ошибка при скачивании файла")
    else:
        print(f"Файл успешно скачан: {dest_path}")

# Функция для сохранения установленных версий в файл
def save_installed_versions(no_update_needed, to_update):
    with open(version_file, 'w') as f:
        for filename, (version, adaptation) in {**no_update_needed, **to_update}.items():
            f.write(f"{filename}, версия: {version}, адаптация: {adaptation}\n")

# Главная функция
def main():
    installed_files = get_installed_files()
    json_files = get_json_files()

    # Сравниваем файлы
    to_update, no_update_needed = compare_files(installed_files, json_files)

    # Выводим список файлов для обновления и тех, которые не требуют обновления
    print("\nПриложения, которые будут обновлены:")
    for filename, (version, adaptation) in to_update.items():
        print(f"  {filename} (новая версия: {version}, адаптация: {adaptation})")

    print("\nПриложения, которые уже установлены и не требуют обновления:")
    for filename, (version, adaptation) in no_update_needed.items():
        print(f"  {filename} (текущая версия: {version}, адаптация: {adaptation})")

    # Запрашиваем подтверждение
    confirmation = input("\nХотите обновить перечисленные файлы? (y/n): ").strip().lower()

    if confirmation == 'y':
        for filename, (version, adaptation) in to_update.items():
            apk_url = f"{apk_base_url}{filename}.apk"
            apk_path = os.path.join(apk_directory, f"{filename}.apk")
            print(f"Обновление: {apk_url}")
            download_file_with_progress(apk_url, apk_path)
        print("\nОбновление завершено.")

    # Сохраняем установленные версии в файл
    save_installed_versions(no_update_needed, to_update)
    print(f"\nСписок установленных версий сохранён в файл '{version_file}'.")

if __name__ == "__main__":
    from tqdm import tqdm
    main()
