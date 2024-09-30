import subprocess
import sys
import requests
import os
import commentjson as json  # Используем commentjson для разбора JSON с комментариями
from colorama import Fore, Style, init
from tqdm import tqdm  # Модуль для прогресс-бара

special_apps = [
    {
        "package_name": "com.carWizard.li.swmb",
        "permissions": [
            "android.permission.REQUEST_INSTALL_PACKAGES",
            "android.permission.WRITE_SECURE_SETTINGS"
        ],
        "additional_commands": [
            {"cmd": "appops set com.carWizard.li.swmb REQUEST_INSTALL_PACKAGES allow"}
        ]
    },
    {
        "package_name": "ru.encars.lixiangtweaks",
        "permissions": [
            "android.permission.SYSTEM_ALERT_WINDOW"
        ],
        "additional_commands": []
    },
    {
        "package_name": "air.StrelkaHUDFREE",
        "permissions": [
            "android.permission.SYSTEM_ALERT_WINDOW"
        ],
        "additional_commands": [
            {"cmd": "dumpsys deviceidle whitelist +air.StrelkaHUDFREE"}
        ]
    },
    {
        "package_name": "com.mybedy.antiradar",
        "permissions": [
            "android.permission.SYSTEM_ALERT_WINDOW"
        ],
        "additional_commands": [
            {"cmd": "dumpsys deviceidle whitelist +com.mybedy.antiradar"}
        ]
    }
]

# Инициализируем colorama
init(autoreset=True)

def get_connected_devices():
    """Список подключенных ADB-устройств."""
    result = subprocess.run(['adb', 'devices'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lines = result.stdout.strip().split('\n')
    devices = []
    for line in lines[1:]:
        if '\tdevice' in line:
            devices.append(line.split('\t')[0])
    return devices

def select_device(devices):
    """Позволяет выбрать устройство по номеру."""
    if not devices:
        print(Fore.RED + "Нет подключенных устройств ADB.")
        sys.exit(1)
    elif len(devices) == 1:
        print(Fore.YELLOW + f"Используется устройство: {devices[0]}")
        return devices[0]
    else:
        print(Fore.YELLOW + "Выберите устройство:")
        for i, device in enumerate(devices):
            print(f"{i+1}: {device}")
        while True:
            choice = input("Введите номер устройства: ")
            try:
                index = int(choice) - 1
                if 0 <= index < len(devices):
                    return devices[index]
                else:
                    print(Fore.RED + "Неверный выбор. Попробуйте снова.")
            except ValueError:
                print(Fore.RED + "Неверный ввод. Пожалуйста, введите число.")

import re

def get_users(device):
    """Получает список профилей пользователей на устройстве."""
    result = subprocess.run(['adb', '-s', device, 'shell', 'pm', 'list', 'users'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(Fore.RED + "Ошибка при получении списка пользователей:", result.stderr)
        sys.exit(1)
    lines = result.stdout.strip().split('\n')
    users = []
    for line in lines:
        match = re.search(r'UserInfo\{(\d+):', line)
        if match:
            user_id = match.group(1)
            users.append(user_id)
    return users


def check_app_installed(device, user_id, package_name):
    """Проверяет, установлено ли приложение для заданного пользователя."""
    result = subprocess.run(['adb', '-s', device, 'shell', 'pm', 'list', 'packages', '--user', user_id],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(Fore.RED + f"Ошибка при проверке установленных приложений для пользователя {user_id}:", result.stderr)
        return False
    return package_name in result.stdout

def get_app_version(device, user_id, package_name):
    """Получает установленную версию приложения для заданного пользователя."""
    result = subprocess.run(['adb', '-s', device, 'shell', 'dumpsys', 'package', package_name],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return None
    for line in result.stdout.strip().split('\n'):
        if 'versionName=' in line:
            return line.strip().split('versionName=')[1]
    return None

def check_app_permission(device, user_id, package_name, permission):
    """Проверяет, выдано ли указанное разрешение для приложения."""
    result = subprocess.run(['adb', '-s', device, 'shell', 'appops', 'get', '--user', user_id, package_name],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(Fore.RED + f"Ошибка при получении разрешений для пользователя {user_id}:", result.stderr)
        return None
    for line in result.stdout.strip().split('\n'):
        if permission in line:
            if 'allow' in line:
                return 'allow'
            elif 'deny' in line:
                return 'deny'
            else:
                return 'unknown'
    return 'not set'

def grant_app_permission(device, user_id, package_name, permission):
    """Выдает указанное разрешение приложению."""
    result = subprocess.run(['adb', '-s', device, 'shell', 'appops', 'set', '--user', user_id, package_name, permission, 'allow'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(Fore.RED + f"Ошибка при установке разрешения для пользователя {user_id}:", result.stderr)
        return False
    return True

def download_store_apk(url, filename):
    """Скачивает APK магазина по указанному URL с прогресс-баром."""
    print(Fore.YELLOW + f"Скачивание APK из {url}...")
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Килобайт
        t = tqdm(total=total_size, unit='iB', unit_scale=True)
        with open(filename, 'wb') as f:
            for data in response.iter_content(block_size):
                t.update(len(data))
                f.write(data)
        t.close()
        if total_size != 0 and t.n != total_size:
            print(Fore.RED + "Ошибка при скачивании APK: Размер файла не соответствует ожидаемому.")
            return False
        print(Fore.GREEN + "APK успешно скачан.")
        return True
    else:
        print(Fore.RED + f"Ошибка при скачивании APK: HTTP {response.status_code}")
        return False

def install_apk(device, apk_path, user_id=None):
    """Устанавливает APK на устройство. Если указан user_id, устанавливает для конкретного пользователя."""
    print(Fore.YELLOW + f"Установка APK {apk_path} на устройство...")
    cmd = ['adb', '-s', device, 'install', '-r']
    if user_id is not None:
        cmd.extend(['--user', user_id])
    cmd.append(apk_path)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0 or 'Success' not in result.stdout:
        print(Fore.RED + "Ошибка при установке APK:", result.stderr)
        return False
    print(Fore.GREEN + "APK успешно установлен.")
    return True

def force_stop_app(device, user_id, package_name):
    """Выполняет force-stop приложения для заданного пользователя."""
    result = subprocess.run(['adb', '-s', device, 'shell', 'am', 'force-stop', '--user', user_id, package_name],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(Fore.RED + f"Ошибка при выполнении force-stop для пользователя {user_id}:", result.stderr)
        return False
    print(Fore.GREEN + f"Приложение {package_name} остановлено для пользователя {user_id}.")
    return True

def uninstall_app(device, user_id, package_name):
    """Удаляет приложение для заданного пользователя."""
    result = subprocess.run(['adb', '-s', device, 'uninstall', '--user', user_id, package_name],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0 or 'Success' not in result.stdout:
        print(Fore.RED + f"Ошибка при удалении приложения для пользователя {user_id}:", result.stderr)
        return False
    print(Fore.GREEN + f"Приложение {package_name} удалено для пользователя {user_id}.")
    return True

def get_installed_keyboards(device, user_id):
    """Получает список установленных клавиатур для заданного пользователя."""
    result = subprocess.run(['adb', '-s', device, 'shell', 'ime', 'list', '-a', '--user', user_id],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(Fore.RED + f"Ошибка при получении списка клавиатур для пользователя {user_id}:", result.stderr.strip())
        return []
    lines = result.stdout.strip().split('\n')
    keyboards = []
    for line in lines:
        if 'mId=' in line:
            ime_id = line.strip().split('mId=')[1].split()[0]
            keyboards.append(ime_id)
    return keyboards

def get_default_keyboard(device, user_id):
    """Получает текущую клавиатуру по умолчанию для заданного пользователя."""
    result = subprocess.run(['adb', '-s', device, 'shell', 'settings', 'get', 'secure', 'default_input_method', '--user', user_id],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(Fore.RED + f"Ошибка при получении текущей клавиатуры для пользователя {user_id}:", result.stderr.strip())
        return None
    return result.stdout.strip()

def install_app_for_user(device, user_id, package_name):
    """Устанавливает приложение для заданного пользователя, если оно не установлено."""
    # Проверяем, установлено ли приложение для пользователя
    installed = check_app_installed(device, user_id, package_name)
    if not installed:
        print(Fore.YELLOW + f"Приложение {package_name} не установлено для пользователя {user_id}. Устанавливаем...")
        result = subprocess.run(['adb', '-s', device, 'shell', 'pm', 'install-existing', '--user', user_id, package_name],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(Fore.RED + f"Ошибка при установке приложения для пользователя {user_id}: {result.stderr.strip()}")
            return False
        print(Fore.GREEN + f"Приложение {package_name} установлено для пользователя {user_id}.")
    return True

def change_keyboard(device):
    """Меняет клавиатуру по умолчанию для всех пользователей."""
    users = get_users(device)
    for user_id in users:
        print(Fore.CYAN + f"\nПользователь {user_id}:")
        keyboards = get_installed_keyboards(device, user_id)
        if not keyboards:
            print(Fore.RED + "Клавиатуры не найдены.")
            continue
        default_keyboard = get_default_keyboard(device, user_id)
        if default_keyboard:
            print(Fore.YELLOW + f"Текущая клавиатура: {default_keyboard}")
        else:
            print(Fore.RED + "Не удалось определить текущую клавиатуру.")
        print(Fore.YELLOW + "Доступные клавиатуры:")
        for i, keyboard in enumerate(keyboards):
            if keyboard == default_keyboard:
                print(f"{i+1}) {Fore.GREEN}{keyboard} (Текущая){Style.RESET_ALL}")
            else:
                print(f"{i+1}) {keyboard}")
        while True:
            choice = input("Введите номер клавиатуры, которую хотите установить по умолчанию: ")
            try:
                index = int(choice) - 1
                if 0 <= index < len(keyboards):
                    selected_keyboard = keyboards[index]
                    break
                else:
                    print(Fore.RED + "Неверный выбор. Попробуйте снова.")
            except ValueError:
                print(Fore.RED + "Неверный ввод. Пожалуйста, введите число.")
        # Получаем имя пакета клавиатуры
        keyboard_package = selected_keyboard.split('/')[0]
        # Устанавливаем клавиатуру для пользователя, если не установлена
        install_app_for_user(device, user_id, keyboard_package)
        # Включаем выбранную клавиатуру
        print(Fore.YELLOW + f"Включение выбранной клавиатуры: {selected_keyboard}")
        result_enable = subprocess.run(['adb', '-s', device, 'shell', 'ime', 'enable', selected_keyboard, '--user', user_id],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result_enable.returncode != 0:
            print(Fore.RED + f"Ошибка при включении клавиатуры для пользователя {user_id}: {result_enable.stderr.strip()}")
            continue
        # Устанавливаем выбранную клавиатуру по умолчанию
        print(Fore.YELLOW + f"Установка выбранной клавиатуры по умолчанию для пользователя {user_id}")
        result_set = subprocess.run(['adb', '-s', device, 'shell', 'ime', 'set', selected_keyboard, '--user', user_id],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result_set.returncode != 0:
            print(Fore.RED + f"Ошибка при установке клавиатуры по умолчанию для пользователя {user_id}: {result_set.stderr.strip()}")
            continue
        # Отключаем текущую клавиатуру (если она отличается от выбранной)
        if default_keyboard and default_keyboard != selected_keyboard:
            print(Fore.YELLOW + f"Отключение предыдущей клавиатуры: {default_keyboard}")
            result_disable = subprocess.run(['adb', '-s', device, 'shell', 'ime', 'disable', default_keyboard, '--user', user_id],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result_disable.returncode != 0:
                print(Fore.RED + f"Ошибка при отключении клавиатуры для пользователя {user_id}: {result_disable.stderr.strip()}")
        print(Fore.GREEN + f"Клавиатура успешно изменена на {selected_keyboard} для пользователя {user_id}")

def load_app_list():
    """Загружает список приложений из удаленного JSON."""
    url = 'https://store.anyapp.tech/liappstore//apps_prod.json'
    print(Fore.YELLOW + f"Загрузка списка приложений из {url}...")
    response = requests.get(url)
    if response.status_code == 200:
        try:
            app_list = json.loads(response.text)
            print(Fore.GREEN + "Список приложений успешно загружен.")
            return app_list
        except json.JSONDecodeError as e:
            print(Fore.RED + f"Ошибка при разборе JSON: {e}")
            return []
    else:
        print(Fore.RED + f"Ошибка при загрузке списка приложений: HTTP {response.status_code}")
        return []

def load_apk_names():
    """Загружает список пакетов для установки из файла apk_names.txt."""
    apk_names_file = 'apk_names.txt'
    if not os.path.exists(apk_names_file):
        print(Fore.RED + f"Файл {apk_names_file} не найден.")
        return [], []
    with open(apk_names_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    user0_packages = []
    other_users_packages = []
    current_list = None
    for line in lines:
        line = line.strip()
        if line.startswith('#'):
            if 'Пользователь 0' in line:
                current_list = user0_packages
            elif 'Другие пользователи' in line:
                current_list = other_users_packages
            else:
                current_list = None
        elif line and current_list is not None:
            current_list.append(line)
    return user0_packages, other_users_packages

def get_apk_versions():
    """Загружает информацию о версиях приложений из локального файла apk_versions.json."""
    versions_file = os.path.join('apk', 'apk_versions.json')
    if os.path.exists(versions_file):
        with open(versions_file, 'r', encoding='utf-8') as f:
            versions = json.load(f)
    else:
        versions = {}
    return versions

def save_apk_versions(versions):
    """Сохраняет информацию о версиях приложений в локальный файл apk_versions.json."""
    versions_file = os.path.join('apk', 'apk_versions.json')
    with open(versions_file, 'w', encoding='utf-8') as f:
        json.dump(versions, f, indent=4, ensure_ascii=False)

def install_applications(device):
    """Основная функция для установки приложений с прогресс-баром при скачивании."""
    app_list = load_app_list()
    if not app_list:
        print(Fore.RED + "Список приложений пуст. Прерывание установки.")
        return

    user0_packages, other_users_packages = load_apk_names()
    if not user0_packages and not other_users_packages:
        print(Fore.RED + "Списки приложений для установки пусты. Прерывание установки.")
        return
    
    # Вывод загруженных списков пакетов для отладки
    print(Fore.CYAN + f"Пакеты для пользователя 0: {user0_packages}")
    print(Fore.CYAN + f"Пакеты для других пользователей: {other_users_packages}")

    # Проверка на пересечение пакетов между списками
    # overlapping_packages = set(user0_packages) & set(other_users_packages)
    # if overlapping_packages:
    #     print(Fore.RED + f"Ошибка: следующие пакеты указаны для установки и для пользователя 0, и для других пользователей: {', '.join(overlapping_packages)}")
    #     # Решение: удалить пересекающиеся пакеты из списка других пользователей
    #     other_users_packages = [pkg for pkg in other_users_packages if pkg not in overlapping_packages]
    #     print(Fore.YELLOW + f"Удалены пересекающиеся пакеты из других пользователей: {', '.join(overlapping_packages)}")
    
    apk_folder = 'apk'
    if not os.path.exists(apk_folder):
        os.makedirs(apk_folder)

    versions = get_apk_versions()
    users = get_users(device)
    other_users = [user for user in users if user != '0']

    for app in app_list:
        package_name = app.get('package')
        if not package_name:
            continue
        filename = app.get('filename')
        version = app.get('version')
        if not filename or not version:
            continue
        apk_url = f"https://store.anyapp.tech/liappstore/apps/{filename}.apk"
        apk_path = os.path.join(apk_folder, f"{filename}.apk")
        # Проверяем, нужно ли устанавливать для пользователя 0
        install_for_user0 = package_name in user0_packages
        install_for_others = package_name in other_users_packages
        if not install_for_user0 and not install_for_others:
            continue  # Пропускаем приложение, если оно не указано для установки
        
        # Вывод информации для отладки
        print(Fore.CYAN + f"Обрабатываем приложение: {package_name}")
        print(Fore.CYAN + f"Устанавливать для пользователя 0: {install_for_user0}")
        print(Fore.CYAN + f"Устанавливать для других пользователей: {install_for_others}")
        
        # Проверяем, есть ли новая версия
        local_version = versions.get(package_name)
        if local_version != version or not os.path.exists(apk_path):
            print(Fore.YELLOW + f"\nОбнаружена новая версия для {package_name}: {version}")
            print(Fore.YELLOW + f"Скачивание APK из {apk_url}...")
            response = requests.get(apk_url, stream=True)
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024  # 1 Килобайт
                t = tqdm(total=total_size, unit='iB', unit_scale=True)
                with open(apk_path, 'wb') as f:
                    for data in response.iter_content(block_size):
                        t.update(len(data))
                        f.write(data)
                t.close()
                if total_size != 0 and t.n != total_size:
                    print(Fore.RED + "Ошибка при скачивании APK: Размер файла не соответствует ожидаемому.")
                    continue
                print(Fore.GREEN + f"APK {filename}.apk успешно скачан.")
                versions[package_name] = version
                save_apk_versions(versions)
            else:
                print(Fore.RED + f"Ошибка при скачивании APK: HTTP {response.status_code}")
                continue
        else:
            print(Fore.GREEN + f"\nУстановлена последняя версия {package_name}: {version}")
        
        # Установка для пользователя 0
        if install_for_user0:
            print(Fore.YELLOW + f"Установка {package_name} для пользователя 0")
            success = install_apk(device, apk_path, user_id='0')
            if not success:
                print(Fore.RED + f"Не удалось установить {package_name} для пользователя 0")
                continue
        
        # Установка для других пользователей
        if install_for_others:
            for user_id in other_users:
                print(Fore.YELLOW + f"Установка {package_name} для пользователя {user_id}")
                success = install_apk(device, apk_path, user_id=user_id)
                if not success:
                    print(Fore.RED + f"Не удалось установить {package_name} для пользователя {user_id}")
                    continue

def check_special_permissions(device):
    """Проверяет, выданы ли специальные разрешения указанным приложениям."""
    for app in special_apps:
        package_name = app["package_name"]
        permissions = app["permissions"]
        
        print(Fore.CYAN + f"\nПроверка разрешений для приложения {package_name}:")
        
        for permission in permissions:
            # Проверяем статус разрешения через appops
            print(Fore.YELLOW + f"Проверка разрешения {permission}...")
            # Используем команду appops get для проверки разрешений
            # Некоторые разрешения могут требовать специального подхода
            result = subprocess.run(['adb', '-s', device, 'shell', 'appops', 'get', package_name, permission, '--user', '0'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print(Fore.RED + f"Ошибка при проверке разрешения {permission}: {result.stderr.strip()}")
                continue
            output = result.stdout.strip()
            if 'allow' in output:
                print(Fore.GREEN + f"Разрешение {permission} выдано.")
            elif 'deny' in output:
                print(Fore.RED + f"Разрешение {permission} отклонено.")
            else:
                print(Fore.YELLOW + f"Разрешение {permission} не установлено.")
        
        # Проверка дополнительных команд, например, whitelist
        additional_commands = app.get("additional_commands", [])
        for command in additional_commands:
            if 'whitelist' in command["cmd"]:
                # Извлекаем пакет из команды
                match = re.search(r'whitelist \+?(\S+)', command["cmd"])
                if match:
                    pkg = match.group(1)
                    print(Fore.YELLOW + f"Проверка whitelist для {pkg}...")
                    # Проверяем, добавлен ли пакет в whitelist
                    result = subprocess.run(['adb', '-s', device, 'shell', 'dumpsys', 'deviceidle', 'whitelist'],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if result.returncode != 0:
                        print(Fore.RED + f"Ошибка при проверке whitelist: {result.stderr.strip()}")
                        continue
                    if pkg in result.stdout:
                        print(Fore.GREEN + f"{pkg} находится в whitelist.")
                    else:
                        print(Fore.RED + f"{pkg} НЕ находится в whitelist.")
    print(Fore.CYAN + "\nПроверка специальных разрешений завершена.")

def grant_special_permissions(device):
    """Выдает специальные разрешения указанным приложениям."""
    for app in special_apps:
        package_name = app["package_name"]
        permissions = app["permissions"]
        additional_commands = app.get("additional_commands", [])
        
        print(Fore.CYAN + f"\nВыдача разрешений для приложения {package_name}:")
        
        # Выдача стандартных разрешений
        for permission in permissions:
            print(Fore.YELLOW + f"Выдача разрешения {permission}...")
            result = subprocess.run(['adb', '-s', device, 'shell', 'pm', 'grant', package_name, permission],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                print(Fore.GREEN + f"Разрешение {permission} выдано.")
            else:
                print(Fore.RED + f"Ошибка при выдаче разрешения {permission}: {result.stderr.strip()}")
        
        # Выполнение дополнительных команд
        for command in additional_commands:
            cmd_str = command["cmd"]
            print(Fore.YELLOW + f"Выполнение команды: adb shell {cmd_str}")
            cmd_parts = ['adb', '-s', device, 'shell'] + cmd_str.split()
            result = subprocess.run(cmd_parts, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                print(Fore.GREEN + "Команда выполнена успешно.")
            else:
                print(Fore.RED + f"Ошибка при выполнении команды: {result.stderr.strip()}")



def main():
    # Информация о приложениях
    apps = {
        'liapp': {
            'package_name': 'com.lixiang.chat.store',
            'permission': 'android.permission.REQUEST_INSTALL_PACKAGES',
            'config_url': 'https://store.anyapp.tech/liappstore/config.json',
            'apk_filename_template': 'liapp-{version}.apk',
            'version_key': 'version',
            'apk_url_key': 'storeUpdateAPK'
        },
        'rustore': {
            'package_name': 'ru.vk.store',
            'permission': 'android.permission.REQUEST_INSTALL_PACKAGES',
            'apk_url': 'https://static.rustore.ru/release/RuStore.apk',
            'apk_filename': 'RuStore.apk'
        }
    }

    # Список специальных приложений (добавьте этот список вне функции main() или в глобальной области видимости)


    devices = get_connected_devices()
    device = select_device(devices)

    while True:
        print(Fore.CYAN + "\nВыберите действие:")
        print("1: Проверить приложения и разрешения")
        print("2: Скачать приложение LiApp Store")
        print("3: Скачать приложение RuStore")
        print("4: Установить LiApp Store и выдать права")
        print("5: Установить RuStore и выдать права")
        print("6: Удалить LiApp Store на всех пользователях")
        print("7: Удалить RuStore на всех пользователях")
        print("8: Установка приложений")
        print("9: Смена клавиатуры")
        print("10: Выход")
        print("11: Выдать специальные разрешения приложениям")
        print("12: Проверить специальные разрешения приложениям")
        choice = input("Введите номер действия: ")

        if choice == '1':
            # Проверка приложений и разрешений
            users = get_users(device)
            for app_key, app_info in apps.items():
                package_name = app_info['package_name']
                permission = app_info['permission']
                print(Fore.CYAN + f"\nПроверка приложения {package_name}:")
                print(Fore.CYAN + f"Пользователи на устройстве {device}: {', '.join(users)}")
                for user_id in users:
                    print(Fore.MAGENTA + f"\nПроверка для пользователя {user_id}:")
                    installed = check_app_installed(device, user_id, package_name)
                    if installed:
                        print(Fore.GREEN + f"Приложение {package_name} установлено для пользователя {user_id}")
                        version = get_app_version(device, user_id, package_name)
                        if version:
                            print(Fore.YELLOW + f"Установленная версия: {version}")
                        else:
                            print(Fore.RED + "Не удалось определить версию приложения.")
                        permission_status = check_app_permission(device, user_id, package_name, permission)
                        if permission_status:
                            print(Fore.BLUE + f"Разрешение {permission}: {permission_status}")
                        else:
                            print(Fore.RED + f"Статус разрешения {permission} не может быть определен")
                    else:
                        print(Fore.RED + f"Приложение {package_name} НЕ установлено для пользователя {user_id}")

        elif choice == '2':
            # Скачать приложение LiApp Store
            app_info = apps['liapp']
            config_url = app_info['config_url']
            print(Fore.YELLOW + f"Загрузка конфигурации из {config_url}...")
            response = requests.get(config_url)
            if response.status_code == 200:
                try:
                    config = json.loads(response.text)
                except json.JSONDecodeError as e:
                    print(Fore.RED + f"Ошибка при разборе JSON: {e}")
                    continue
                version = config.get(app_info['version_key'])
                apk_url = config.get(app_info['apk_url_key'])
                if version and apk_url:
                    print(Fore.GREEN + f"Последняя версия: {version}")
                    apk_filename = app_info['apk_filename_template'].format(version=version)
                    if os.path.exists(apk_filename):
                        print(Fore.GREEN + f"APK уже скачан: {apk_filename}")
                    else:
                        if download_store_apk(apk_url, apk_filename):
                            print(Fore.GREEN + f"APK скачан как {apk_filename}")
                        else:
                            print(Fore.RED + "Не удалось скачать APK.")
                else:
                    print(Fore.RED + "Не удалось получить информацию о версии или ссылку на APK.")
            else:
                print(Fore.RED + f"Ошибка при загрузке конфигурации: HTTP {response.status_code}")

        elif choice == '3':
            # Скачать приложение RuStore
            app_info = apps['rustore']
            apk_url = app_info['apk_url']
            apk_filename = app_info['apk_filename']
            if os.path.exists(apk_filename):
                print(Fore.GREEN + f"APK уже скачан: {apk_filename}")
            else:
                if download_store_apk(apk_url, apk_filename):
                    print(Fore.GREEN + f"APK скачан как {apk_filename}")
                else:
                    print(Fore.RED + "Не удалось скачать APK.")

        elif choice == '4':
            # Установить LiApp Store и выдать права
            app_info = apps['liapp']
            package_name = app_info['package_name']
            permission = app_info['permission']
            config_url = app_info['config_url']
            print(Fore.YELLOW + f"Загрузка конфигурации из {config_url}...")
            response = requests.get(config_url)
            if response.status_code == 200:
                try:
                    config = json.loads(response.text)
                except json.JSONDecodeError as e:
                    print(Fore.RED + f"Ошибка при разборе JSON: {e}")
                    continue
                version = config.get(app_info['version_key'])
                if version:
                    apk_filename = app_info['apk_filename_template'].format(version=version)
                    if not os.path.exists(apk_filename):
                        print(Fore.RED + f"APK не найден: {apk_filename}. Сначала скачайте APK, выбрав опцию 2.")
                        continue
                    # Установка APK на устройство
                    if install_apk(device, apk_filename):
                        # Выдача прав на всех пользователях
                        users = get_users(device)
                        for user_id in users:
                            print(Fore.MAGENTA + f"Выдача разрешений для пользователя {user_id}...")
                            success = grant_app_permission(device, user_id, package_name, permission)
                            if success:
                                print(Fore.GREEN + f"Разрешение {permission} выдано для пользователя {user_id}")
                            else:
                                print(Fore.RED + f"Не удалось выдать разрешение для пользователя {user_id}")
                    else:
                        print(Fore.RED + "Не удалось установить APK на устройство.")
                else:
                    print(Fore.RED + "Не удалось получить информацию о версии.")
            else:
                print(Fore.RED + f"Ошибка при загрузке конфигурации: HTTP {response.status_code}")

        elif choice == '5':
            # Установить RuStore и выдать права
            app_info = apps['rustore']
            package_name = app_info['package_name']
            permission = app_info['permission']
            apk_filename = app_info['apk_filename']
            if not os.path.exists(apk_filename):
                print(Fore.RED + f"APK не найден: {apk_filename}. Сначала скачайте APK, выбрав опцию 3.")
                continue
            # Установка APK на устройство
            if install_apk(device, apk_filename):
                # Выдача прав на всех пользователях
                users = get_users(device)
                for user_id in users:
                    print(Fore.MAGENTA + f"Выдача разрешений для пользователя {user_id}...")
                    success = grant_app_permission(device, user_id, package_name, permission)
                    if success:
                        print(Fore.GREEN + f"Разрешение {permission} выдано для пользователя {user_id}")
                    else:
                        print(Fore.RED + f"Не удалось выдать разрешение для пользователя {user_id}")
            else:
                print(Fore.RED + "Не удалось установить APK на устройство.")

        elif choice == '6':
            # Удалить LiApp Store на всех пользователях
            app_info = apps['liapp']
            package_name = app_info['package_name']
            users = get_users(device)
            for user_id in users:
                print(Fore.MAGENTA + f"\nОстановка и удаление приложения {package_name} для пользователя {user_id}:")
                force_stop_app(device, user_id, package_name)
                success = uninstall_app(device, user_id, package_name)
                if not success:
                    print(Fore.RED + f"Не удалось удалить приложение для пользователя {user_id}")

        elif choice == '7':
            # Удалить RuStore на всех пользователях
            app_info = apps['rustore']
            package_name = app_info['package_name']
            users = get_users(device)
            for user_id in users:
                print(Fore.MAGENTA + f"\nОстановка и удаление приложения {package_name} для пользователя {user_id}:")
                force_stop_app(device, user_id, package_name)
                success = uninstall_app(device, user_id, package_name)
                if not success:
                    print(Fore.RED + f"Не удалось удалить приложение для пользователя {user_id}")

        elif choice == '8':
            # Установка приложений
            install_applications(device)

        elif choice == '9':
            # Смена клавиатуры
            change_keyboard(device)

        elif choice == '10':
            print(Fore.CYAN + "Выход из программы.")
            break

        elif choice == '11':
            # Выдать специальные разрешения приложениям
            grant_special_permissions(device)

        elif choice == '12':
            # Проверить специальные разрешения приложениям
            check_special_permissions(device)

        else:
            print(Fore.RED + "Неверный выбор действия.")

if __name__ == '__main__':
    main()
