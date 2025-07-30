#!/usr/bin/env python3
import os
import sys
import time
import socket
import subprocess
from datetime import datetime
import argparse
from colorama import init, Fore, Back, Style

# Инициализация colorama для цветного вывода
init(autoreset=True)

def clear_screen():
    """Очистка экрана терминала"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Вывод красивого баннера"""
    clear_screen()
    banner = f"""
{Fore.CYAN}
╔══════════════════════════════════════════════════════════╗
║{Fore.YELLOW}          ПИНГ-ЧЕКЕР - ПРОВЕРКА ДОСТУПНОСТИ СЕРВЕРОВ      {Fore.CYAN}║
╚══════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
"""
    print(banner)

def is_valid_ip(address):
    """Проверка, является ли строка валидным IP-адресом"""
    try:
        socket.inet_aton(address)
        return True
    except:
        return False

def is_valid_hostname(hostname):
    """Проверка, является ли строка валидным доменным именем"""
    try:
        socket.gethostbyname(hostname)
        return True
    except:
        return False

def check_ping(target, count=4, timeout=2):
    """
    Проверяет доступность хоста с помощью ping
    Возвращает словарь с результатами
    """
    result = {
        'target': target,
        'available': False,
        'packet_loss': 100,
        'avg_response': 0,
        'errors': []
    }
    
    # Определяем команду ping в зависимости от ОС
    if sys.platform.startswith('win'):
        ping_cmd = ['ping', '-n', str(count), '-w', str(timeout*1000), target]
    else:
        ping_cmd = ['ping', '-c', str(count), '-W', str(timeout), target]
    
    try:
        output = subprocess.run(
            ping_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout*count + 2
        )
        
        # Анализ вывода ping
        if output.returncode == 0:
            result['available'] = True
            
        # Парсим процент потерь пакетов
        if sys.platform.startswith('win'):
            # Для Windows
            for line in output.stdout.split('\n'):
                if 'Packets: Sent' in line:
                    sent = int(line.split('Sent = ')[1].split(',')[0])
                    received = int(line.split('Received = ')[1].split(',')[0])
                    if sent > 0:
                        result['packet_loss'] = 100 - (received / sent * 100)
                if 'Average = ' in line:
                    avg_ms = line.split('Average = ')[1].replace('ms', '')
                    result['avg_response'] = float(avg_ms)
        else:
            # Для Linux/Mac
            for line in output.stdout.split('\n'):
                if 'packet loss' in line:
                    loss = float(line.split('% packet loss')[0].split(' ')[-1])
                    result['packet_loss'] = loss
                if 'min/avg/max' in line:
                    avg_ms = line.split('=')[1].split('/')[1]
                    result['avg_response'] = float(avg_ms)
                    
    except subprocess.TimeoutExpired:
        result['errors'].append('Превышено время ожидания ping')
    except Exception as e:
        result['errors'].append(f'Ошибка выполнения ping: {str(e)}')
    
    return result

def check_port(target, port, timeout=2):
    """
    Проверяет доступность порта на хосте
    Возвращает словарь с результатами
    """
    result = {
        'target': f"{target}:{port}",
        'available': False,
        'response_time': 0,
        'errors': []
    }
    
    start_time = time.time()
    try:
        with socket.create_connection((target, port), timeout=timeout):
            result['available'] = True
            result['response_time'] = (time.time() - start_time) * 1000  # в мс
    except socket.timeout:
        result['errors'].append(f"Таймаут соединения с портом {port}")
    except ConnectionRefusedError:
        result['errors'].append(f"Соединение отклонено на порту {port}")
    except Exception as e:
        result['errors'].append(f"Ошибка проверки порта: {str(e)}")
    
    return result

def print_result(result, check_type='ping'):
    """Красивый вывод результатов проверки"""
    target = result['target']
    available = result['available']
    errors = result.get('errors', [])
    
    if check_type == 'ping':
        packet_loss = result['packet_loss']
        avg_response = result['avg_response']
        
        status = f"{Fore.GREEN}ДОСТУПЕН{Style.RESET_ALL}" if available else f"{Fore.RED}НЕДОСТУПЕН{Style.RESET_ALL}"
        
        print(f"\n{Fore.YELLOW}Результаты проверки: {target}{Style.RESET_ALL}")
        print(f"  Статус:       {status}")
        print(f"  Потеря пакетов: {packet_loss:.1f}%")
        print(f"  Ср. время ответа: {avg_response:.2f} мс")
        
    elif check_type == 'port':
        response_time = result.get('response_time', 0)
        
        status = f"{Fore.GREEN}ОТКРЫТ{Style.RESET_ALL}" if available else f"{Fore.RED}ЗАКРЫТ{Style.RESET_ALL}"
        
        print(f"\n{Fore.YELLOW}Результаты проверки порта: {target}{Style.RESET_ALL}")
        print(f"  Статус:       {status}")
        if available:
            print(f"  Время ответа: {response_time:.2f} мс")
    
    if errors:
        print(f"\n{Fore.RED}Ошибки:{Style.RESET_ALL}")
        for error in errors:
            print(f"  - {error}")

def continuous_check(target, interval=5, max_checks=None, port=None):
    """Непрерывная проверка доступности с заданным интервалом"""
    check_count = 0
    print_banner()
    
    try:
        while True:
            if max_checks and check_count >= max_checks:
                break
                
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{Fore.MAGENTA}Проверка #{check_count + 1} | {current_time}{Style.RESET_ALL}")
            
            if port:
                result = check_port(target, port)
                print_result(result, 'port')
            else:
                result = check_ping(target)
                print_result(result, 'ping')
            
            check_count += 1
            if max_checks is None or check_count < max_checks:
                print(f"\n{Fore.BLUE}Следующая проверка через {interval} сек...{Style.RESET_ALL}")
                time.sleep(interval)
                
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Проверка остановлена пользователем.{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(
        description="Пинг-чекер - проверка доступности сайтов и серверов",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        'target',
        help="Цель для проверки (IP-адрес или доменное имя)"
    )
    
    parser.add_argument(
        '-p', '--port',
        type=int,
        help="Проверять конкретный порт вместо ping"
    )
    
    parser.add_argument(
        '-c', '--count',
        type=int,
        default=4,
        help="Количество пинг-запросов (по умолчанию: 4)"
    )
    
    parser.add_argument(
        '-t', '--timeout',
        type=int,
        default=2,
        help="Таймаут в секундах (по умолчанию: 2)"
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=5,
        help="Интервал между проверками в секундах (по умолчанию: 5)"
    )
    
    parser.add_argument(
        '-m', '--max-checks',
        type=int,
        help="Максимальное количество проверок (по умолчанию: бесконечно)"
    )
    
    args = parser.parse_args()
    
    # Валидация цели
    if not (is_valid_ip(args.target) or is_valid_hostname(args.target)):
        print(f"{Fore.RED}Ошибка: '{args.target}' не является валидным IP-адресом или доменным именем{Style.RESET_ALL}")
        sys.exit(1)
    
    print_banner()
    
    if args.port:
        print(f"{Fore.CYAN}Начинаю проверку порта {args.port} на {args.target}...{Style.RESET_ALL}")
        continuous_check(args.target, args.interval, args.max_checks, args.port)
    else:
        print(f"{Fore.CYAN}Начинаю ping-проверку {args.target}...{Style.RESET_ALL}")
        continuous_check(args.target, args.interval, args.max_checks)

if __name__ == "__main__":
    main()