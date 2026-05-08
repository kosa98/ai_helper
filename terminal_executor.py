import subprocess
import os
from datetime import datetime

class TerminalExecutor:
    def __init__(self, working_dir=".", user="ai_helper"):
        # Приводим путь к абсолютному, чтобы не было путаницы с cd
        self.working_dir = os.path.abspath(working_dir)
        self.user = user
        self.log_file = os.path.join(self.working_dir, "terminal.log")
        
        if not os.path.exists(self.working_dir):
            try:
                os.makedirs(self.working_dir, exist_ok=True)
                print(f"✅ Создана рабочая директория: {self.working_dir}")
            except Exception as e:
                print(f"❌ Ошибка создания директории: {e}")

    def _log(self, message):
        """Записывает событие в лог-файл и выводит в консоль для отладки."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry) # Чтобы ты видел движуху в основном терминале
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

    def execute(self, command):
        """Выполняет команду через sudo -n (non-interactive)."""
        self._log(f"RUNNING COMMAND: {command}")
        
        # -n гарантирует, что sudo НЕ будет ждать пароля. Если прав нет - он просто упадет.
        wrapped_command = [
            "sudo", "-n", "-u", self.user, 
            "bash", "-c", f"cd '{self.working_dir}' && {command}"
        ]
        
        try:
            # shell=False обязателен при передаче команды списком!
            result = subprocess.run(
                wrapped_command,
                shell=False,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if result.returncode == 0:
                self._log(f"SUCCESS. Output: {stdout if stdout else '[No output]'}")
                return {"status": "success", "stdout": stdout, "stderr": stderr}
            else:
                self._log(f"ERROR (Code {result.returncode}). Stderr: {stderr}")
                return {
                    "status": "error", 
                    "stdout": stdout, 
                    "stderr": stderr, 
                    "code": result.returncode
                }
                
        except subprocess.TimeoutExpired:
            self._log("TIMEOUT EXCEEDED")
            return {"status": "error", "error": "Команда выполнялась слишком долго"}
        except Exception as e:
            self._log(f"CRITICAL EXCEPTION: {str(e)}")
            return {"status": "error", "error": str(e)}

    def write_file(self, filename, content):
        """Записывает файл напрямую через sudo tee (самый надежный способ)."""
        self._log(f"ATTEMPTING TO WRITE FILE: {filename}")
        path = os.path.join(self.working_dir, filename)
        
        try:
            # -n тут тоже важен
            cmd = ["sudo", "-n", "-u", self.user, "tee", path]
            # Запускаем процесс и через stdin "вливаем" в него содержимое файла
            process = subprocess.Popen(
                cmd, 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            stdout, stderr = process.communicate(input=content)
            
            if process.returncode == 0:
                self._log(f"FILE {filename} WRITTEN SUCCESSFULLY")
                return {"status": "success", "stdout": f"Файл {filename} записан."}
            else:
                self._log(f"WRITE ERROR: {stderr}")
                return {"status": "error", "stderr": stderr}
        except Exception as e:
            self._log(f"WRITE CRITICAL: {str(e)}")
            return {"status": "error", "error": str(e)}