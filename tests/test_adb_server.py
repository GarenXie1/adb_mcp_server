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


class AdbRootTests(unittest.TestCase):
    def test_restarts_adbd_as_root_on_selected_device(self):
        device = Mock(serial="emulator-5554")

        with patch.object(adb_server, "get_device", return_value=device) as get_device:
            result = asyncio.run(adb_server.adb_root("emulator-5554"))

        get_device.assert_called_once_with("emulator-5554")
        device.root.assert_called_once_with()
        self.assertEqual(result, "设备 emulator-5554 的 adbd 已切换为 root 模式")

    def test_treats_already_root_as_success(self):
        device = Mock(serial="emulator-5554")
        device.root.side_effect = RuntimeError("adbd is already running as root")

        with patch.object(adb_server, "get_device", return_value=device):
            result = asyncio.run(adb_server.adb_root("emulator-5554"))

        self.assertEqual(result, "设备 emulator-5554 的 adbd 已处于 root 模式")


class AdbRemountTests(unittest.TestCase):
    def test_roots_then_remounts_the_same_device(self):
        device = Mock(serial="emulator-5554")
        remount_device = Mock(serial="emulator-5554")

        with patch.object(
            adb_server,
            "get_device",
            side_effect=[device, remount_device],
        ) as get_device:
            result = asyncio.run(adb_server.adb_remount("emulator-5554"))

        self.assertEqual(
            get_device.call_args_list,
            [unittest.mock.call("emulator-5554"), unittest.mock.call("emulator-5554")],
        )
        device.root.assert_called_once_with()
        remount_device.remount.assert_called_once_with()
        self.assertEqual(result, "设备 emulator-5554 已成功以可写方式重新挂载")

    def test_retries_remount_while_adbd_restarts(self):
        device = Mock(serial="emulator-5554")
        remount_device = Mock(serial="emulator-5554")
        remount_device.remount.side_effect = [RuntimeError("device offline"), None]

        with patch.object(
            adb_server,
            "get_device",
            side_effect=[device, remount_device, remount_device],
        ), patch.object(adb_server.time, "monotonic", return_value=0), patch.object(
            adb_server.time, "sleep"
        ) as sleep:
            result = asyncio.run(adb_server.adb_remount("emulator-5554"))

        sleep.assert_called_once_with(adb_server.ADB_ROOT_RETRY_INTERVAL_SECONDS)
        self.assertEqual(result, "设备 emulator-5554 已成功以可写方式重新挂载")


if __name__ == "__main__":
    unittest.main()
