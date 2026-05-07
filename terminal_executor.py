import subprocess
import os
from datetime import datetime

class TerminalExecutor:
    def __init__(self, working_dir=".", user="ai_helper"):
        self.working_dir = working_dir
        self.user = user
        self.log_file = os.path.join(self.working_dir, "terminal.log")
        
        if not os.path.exists(self.working_dir):
            try:
                print("CCCCC")
                os.makedirs(self.working_dir)
            except:
                print("BBBBB")
                pass

    def _log(self, message):
        """Записывает событие в лог-файл."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("AAAAA")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")

    def execute(self, command):
        """Выполняет команду и логирует всё: и ввод, и вывод."""
        self._log(f"RUNNING COMMAND: {command}")
        
        wrapped_command = f"sudo -u {self.user} bash -c 'cd {self.working_dir} && {command}'"
        
        try:
            result = subprocess.run(
                wrapped_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if result.returncode == 0:
                self._log(f"SUCCESS. Output: {stdout}")
                return {"status": "success", "stdout": stdout, "stderr": stderr}
            else:
                self._log(f"ERROR (Code {result.returncode}). Stderr: {stderr}")
                return {"status": "error", "stdout": stdout, "stderr": stderr, "code": result.returncode}
                
        except Exception as e:
            self._log(f"CRITICAL EXCEPTION: {str(e)}")
            return {"status": "error", "error": str(e)}

    def write_file(self, filename, content):
        """Альтернативный метод записи через Python (более надежный, чем echo)."""
        self._log(f"ATTEMPTING TO WRITE FILE: {filename}")
        try:
            # Сначала создаем файл от имени основного юзера, потом меняем владельца
            path = os.path.join(self.working_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Меняем владельца на ai_agent, чтобы он мог с ним работать
            os.system(f"sudo chown {self.user} {path}")
            self._log(f"FILE {filename} WRITTEN SUCCESSFULLY")
            return {"status": "success", "stdout": f"Файл {filename} записан."}
        except Exception as e:
            self._log(f"WRITE ERROR: {str(e)}")
            return {"status": "error", "error": str(e)}