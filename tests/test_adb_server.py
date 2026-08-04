import asyncio
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

# Allow running this file directly from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import adb_server


class ExecuteShellCommandTests(unittest.TestCase):
    def test_executes_command_on_selected_device(self):
        device = Mock()
        device.shell.return_value = "directory listing\n"

        with patch.object(adb_server, "get_device", return_value=device) as get_device:
            result = asyncio.run(
                adb_server.execute_shell_command("ls -l /data/", "emulator-5554")
            )

        get_device.assert_called_once_with("emulator-5554")
        device.shell.assert_called_once_with("ls -l /data/")
        self.assertEqual(result, "directory listing\n")

    def test_rejects_empty_command(self):
        result = asyncio.run(adb_server.execute_shell_command("   "))

        self.assertEqual(result, "执行 shell 命令失败: 命令不能为空")


if __name__ == "__main__":
    unittest.main()
