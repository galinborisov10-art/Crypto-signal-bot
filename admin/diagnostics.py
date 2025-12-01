#!/usr/bin/env python3
"""
🔧 Автоматична диагностика и самопоправка на Crypto Signal Bot
Изпълнява се всеки ден в 01:00 UTC (03:00 BG време)
"""

import os
import sys
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path

# Настройки
# Get parent directory of diagnostics.py (which is in admin/) to get the project root
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADMIN_DIR = BASE_DIR / "admin"
LOG_FILE = ADMIN_DIR / "diagnostics.log"

# Конфигурирай logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BotDiagnostics:
    """Система за диагностика и самопоправка"""
    
    def __init__(self):
        self.issues_found = []
        self.fixes_applied = []
        self.report = []
        
    def log(self, message, level="info"):
        """Логира съобщение"""
        self.report.append(f"[{level.upper()}] {message}")
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    
    # ========== ПРОВЕРКА 1: КРИТИЧНИ ФАЙЛОВЕ ==========
    def check_critical_files(self):
        """Проверява дали всички критични файлове съществуват"""
        self.log("🔍 ПРОВЕРКА 1: Критични файлове...")
        
        critical_files = {
            "bot.py": BASE_DIR / "bot.py",
            "bot_stats.json": BASE_DIR / "bot_stats.json",
            "admin_module.py": ADMIN_DIR / "admin_module.py",
            "credentials.json": ADMIN_DIR / "credentials.json",
            "admin_password.json": ADMIN_DIR / "admin_password.json",
            ".gitignore": BASE_DIR / ".gitignore"
        }
        
        for name, path in critical_files.items():
            if not path.exists():
                self.log(f"❌ Липсва критичен файл: {name}", "error")
                self.issues_found.append(f"Missing file: {name}")
                self.fix_missing_file(name, path)
            else:
                self.log(f"✅ {name} - OK")
    
    def fix_missing_file(self, name, path):
        """Възстановява липсващ критичен файл"""
        if name == "bot_stats.json":
            self.log(f"🔧 Създавам {name}...", "warning")
            initial_data = {
                "total_signals": 0,
                "by_symbol": {},
                "by_timeframe": {},
                "by_confidence": {}
            }
            with open(path, 'w') as f:
                json.dump(initial_data, f, indent=2)
            self.fixes_applied.append(f"Created {name}")
            self.log(f"✅ {name} възстановен")
    
    # ========== ПРОВЕРКА 2: СТРУКТУРА НА JSON ФАЙЛОВЕ ==========
    def check_json_integrity(self):
        """Проверява валидността на JSON файловете"""
        self.log("🔍 ПРОВЕРКА 2: JSON файлове...")
        
        json_files = {
            "bot_stats.json": BASE_DIR / "bot_stats.json",
            "credentials.json": ADMIN_DIR / "credentials.json",
            "admin_password.json": ADMIN_DIR / "admin_password.json"
        }
        
        for name, path in json_files.items():
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    self.log(f"✅ {name} - валиден JSON")
                    
                    # Проверка на структурата
                    if name == "bot_stats.json":
                        self.validate_stats_structure(data, path)
                    
                except json.JSONDecodeError as e:
                    self.log(f"❌ {name} - невалиден JSON: {e}", "error")
                    self.issues_found.append(f"Corrupted JSON: {name}")
                    self.fix_corrupted_json(name, path)
    
    def validate_stats_structure(self, data, path):
        """Валидира структурата на bot_stats.json"""
        required_keys = ["total_signals", "by_symbol", "by_timeframe", "by_confidence"]
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            self.log(f"⚠️ bot_stats.json липсват ключове: {missing_keys}", "warning")
            for key in missing_keys:
                if key == "total_signals":
                    data[key] = 0
                else:
                    data[key] = {}
            
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            self.fixes_applied.append("Fixed bot_stats.json structure")
            self.log("✅ bot_stats.json структура поправена")
    
    def fix_corrupted_json(self, name, path):
        """Възстановява повреден JSON файл от backup"""
        backup_dir = ADMIN_DIR / "backups"
        if backup_dir.exists():
            # Търси най-нов backup
            backups = sorted(backup_dir.glob(f"{name}.*"), reverse=True)
            if backups:
                self.log(f"🔧 Възстановявам {name} от backup...", "warning")
                import shutil
                shutil.copy(backups[0], path)
                self.fixes_applied.append(f"Restored {name} from backup")
                self.log(f"✅ {name} възстановен от {backups[0].name}")
            else:
                self.log(f"❌ Няма backup за {name}", "error")
    
    # ========== ПРОВЕРКА 3: ПРОЦЕС НА БОТА ==========
    def check_bot_process(self):
        """Проверява дали ботът работи"""
        self.log("🔍 ПРОВЕРКА 3: Процес на бота...")
        
        import subprocess
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True
            )
            
            if "bot.py" in result.stdout:
                # Извличаме PID
                for line in result.stdout.split('\n'):
                    if "bot.py" in line and "python" in line:
                        pid = line.split()[1]
                        self.log(f"✅ Бот работи (PID: {pid})")
                        return True
            else:
                self.log("❌ Ботът НЕ работи!", "error")
                self.issues_found.append("Bot process not running")
                return False
                
        except Exception as e:
            self.log(f"❌ Грешка при проверка на процеса: {e}", "error")
            return False
    
    # ========== ПРОВЕРКА 4: LOG ФАЙЛОВЕ ==========
    def check_log_files(self):
        """Проверява размера на log файловете"""
        self.log("🔍 ПРОВЕРКА 4: Log файлове...")
        
        log_files = {
            "bot.log": BASE_DIR / "bot.log",
            "diagnostics.log": LOG_FILE
        }
        
        max_size_mb = 50  # Максимален размер 50MB
        
        for name, path in log_files.items():
            if path.exists():
                size_mb = path.stat().st_size / (1024 * 1024)
                
                if size_mb > max_size_mb:
                    self.log(f"⚠️ {name} е твърде голям ({size_mb:.2f}MB)", "warning")
                    self.rotate_log_file(path)
                else:
                    self.log(f"✅ {name} - {size_mb:.2f}MB")
    
    def rotate_log_file(self, path):
        """Ротира голям log файл"""
        self.log(f"🔧 Ротирам {path.name}...", "warning")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_suffix(f".{timestamp}.log")
        
        import shutil
        shutil.move(str(path), str(backup_path))
        path.touch()  # Създай нов празен файл
        
        self.fixes_applied.append(f"Rotated {path.name}")
        self.log(f"✅ {path.name} ротиран към {backup_path.name}")
    
    # ========== ПРОВЕРКА 5: ДИСКОВА ПАМЕТ ==========
    def check_disk_space(self):
        """Проверява свободната дискова памет"""
        self.log("🔍 ПРОВЕРКА 5: Дискова памет...")
        
        import shutil
        stat = shutil.disk_usage(BASE_DIR)
        
        free_gb = stat.free / (1024**3)
        total_gb = stat.total / (1024**3)
        used_percent = (stat.used / stat.total) * 100
        
        self.log(f"💾 Свободно: {free_gb:.2f}GB / {total_gb:.2f}GB ({100-used_percent:.1f}%)")
        
        if free_gb < 1:
            self.log("⚠️ Малко свободно място на диска!", "warning")
            self.issues_found.append("Low disk space")
            self.cleanup_old_backups()
    
    def cleanup_old_backups(self):
        """Изтрива стари backups"""
        self.log("🔧 Почистване на стари backups...", "warning")
        backup_dir = ADMIN_DIR / "backups"
        
        if backup_dir.exists():
            import time
            current_time = time.time()
            retention_days = 30
            retention_seconds = retention_days * 24 * 60 * 60
            
            deleted_count = 0
            for backup_file in backup_dir.iterdir():
                if backup_file.is_file():
                    file_age = current_time - backup_file.stat().st_mtime
                    if file_age > retention_seconds:
                        backup_file.unlink()
                        deleted_count += 1
            
            if deleted_count > 0:
                self.fixes_applied.append(f"Deleted {deleted_count} old backups")
                self.log(f"✅ Изтрити {deleted_count} стари backups")
    
    # ========== ПРОВЕРКА 6: PERMISSIONS ==========
    def check_file_permissions(self):
        """Проверява permissions на скриптове"""
        self.log("🔍 ПРОВЕРКА 6: File permissions...")
        
        executable_files = [
            ADMIN_DIR / "backup.sh",
            ADMIN_DIR / "diagnostics.py"
        ]
        
        for script in executable_files:
            if script.exists():
                is_executable = os.access(script, os.X_OK)
                if not is_executable:
                    self.log(f"⚠️ {script.name} няма execute permission", "warning")
                    os.chmod(script, 0o755)
                    self.fixes_applied.append(f"Fixed permissions: {script.name}")
                    self.log(f"✅ {script.name} permissions поправени")
                else:
                    self.log(f"✅ {script.name} - OK")
    
    # ========== ГЕНЕРИРАНЕ НА ОТЧЕТ ==========
    def generate_report(self):
        """Генерира финален отчет"""
        self.log("=" * 60)
        self.log("📊 ФИНАЛЕН ОТЧЕТ")
        self.log("=" * 60)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        self.log(f"⏰ Време: {timestamp}")
        self.log(f"🔍 Намерени проблеми: {len(self.issues_found)}")
        self.log(f"🔧 Приложени поправки: {len(self.fixes_applied)}")
        
        if self.issues_found:
            self.log("\n❌ ПРОБЛЕМИ:")
            for issue in self.issues_found:
                self.log(f"  - {issue}")
        
        if self.fixes_applied:
            self.log("\n✅ ПОПРАВКИ:")
            for fix in self.fixes_applied:
                self.log(f"  - {fix}")
        
        if not self.issues_found:
            self.log("\n🎉 СИСТЕМАТА Е В ОТЛИЧНО СЪСТОЯНИЕ!")
        
        self.log("=" * 60)
        
        # Запиши отчета във файл
        report_file = ADMIN_DIR / "reports" / "diagnostics" / f"diagnostic_{datetime.now().strftime('%Y%m%d')}.txt"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.report))
        
        self.log(f"\n💾 Отчетът е записан в: {report_file}")
    
    # ========== ГЛАВНА ФУНКЦИЯ ==========
    def run_diagnostics(self):
        """Изпълнява всички проверки"""
        self.log("🚀 СТАРТИРАНЕ НА ДИАГНОСТИКА...")
        self.log(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self.log("=" * 60)
        
        try:
            self.check_critical_files()
            self.check_json_integrity()
            self.check_bot_process()
            self.check_log_files()
            self.check_disk_space()
            self.check_file_permissions()
            
        except Exception as e:
            self.log(f"❌ КРИТИЧНА ГРЕШКА: {e}", "error")
            import traceback
            self.log(traceback.format_exc(), "error")
        
        finally:
            self.generate_report()


def main():
    """Главна функция"""
    diagnostics = BotDiagnostics()
    diagnostics.run_diagnostics()
    
    # Върни exit код според резултата
    if diagnostics.issues_found:
        sys.exit(1)  # Има проблеми
    else:
        sys.exit(0)  # Всичко е ОК


if __name__ == "__main__":
    main()
