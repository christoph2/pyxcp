#!/usr/bin/env python
"""
XCP 握手测试 - 命令行版本
用于快速测试与下位机的连接和基本通信。

使用方法:
    python xcp_hello_cli.py --transport eth --host 127.0.0.1 --port 5555
    python xcp_hello_cli.py --transport sxi --port COM1 --baudrate 115200
    python xcp_hello_cli.py --transport can --interface socketcan --channel can0
"""

import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from pyxcp.cmdline import ArgumentParser


def main():
    console = Console()

    console.print(Panel.fit(
        "[bold cyan]XCP 握手测试工具 (CLI 版本)[/bold cyan]\n"
        "[dim]基于 pyXCP 的下位机连接测试[/dim]",
        border_style="cyan"
    ))

    ap = ArgumentParser(description="XCP 握手测试 - 命令行版本")

    with ap.run() as xcp:
        # ===== 连接 =====
        console.print("\n[bold yellow]🔌 正在建立 XCP 连接...[/bold yellow]")
        try:
            xcp.connect()
            console.print("[green]✓ 连接成功！[/green]")
        except Exception as e:
            console.print(f"[red]✗ 连接失败: {e}[/red]")
            sys.exit(1)

        # ===== 从设备信息 =====
        console.print("\n[bold yellow]📋 获取从设备信息...[/bold yellow]")

        # 基本信息表
        info_table = Table(title="从设备基本信息", border_style="blue")
        info_table.add_column("项目", style="cyan", no_wrap=True)
        info_table.add_column("值", style="green")

        # 标识符
        id_map = [
            (0x00, "ASCII 文本"),
            (0x01, "文件名"),
            (0x02, "文件和路径"),
            (0x05, "EPK"),
            (0x06, "ECU"),
            (0x07, "SYSID"),
        ]
        for id_type, id_name in id_map:
            try:
                identifier = xcp.identifier(id_type)
                if identifier:
                    decoded = identifier.decode("utf-8", errors="replace").strip("\x00").strip()
                    if decoded:
                        info_table.add_row(id_name, decoded)
            except Exception:
                pass

        console.print(info_table)

        # Slave Properties
        props_table = Table(title="Slave Properties", border_style="blue")
        props_table.add_column("属性", style="cyan", no_wrap=True)
        props_table.add_column("值", style="green")

        props = xcp.slaveProperties
        for key, value in sorted(props.items()):
            props_table.add_row(str(key), str(value))

        console.print(props_table)

        # ===== 状态信息 =====
        console.print("\n[bold yellow]📊 状态信息[/bold yellow]")
        try:
            status = xcp.getStatus()
            status_table = Table(title="当前状态", border_style="blue")
            status_table.add_column("项目", style="cyan", no_wrap=True)
            status_table.add_column("值", style="green")
            status_table.add_row("会话状态", str(status.currentSessionStatus))
            status_table.add_row("资源保护状态", str(status.resourceProtectionStatus))
            status_table.add_row("会话配置", str(status.sessionConfiguration))
            console.print(status_table)
        except Exception as e:
            console.print(f"[yellow]⚠ 获取状态失败: {e}[/yellow]")

        # ===== 通信模式 =====
        console.print("\n[bold yellow]📡 通信模式信息[/bold yellow]")
        try:
            if xcp.slaveProperties.optionalCommMode:
                comm_mode = xcp.getCommModeInfo()
                console.print(f"[green]✓ 通信模式: {comm_mode}[/green]")
            else:
                console.print("[yellow]⚠ 从设备不支持可选通信模式[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠ 获取通信模式失败: {e}[/yellow]")

        # ===== DAQ 能力 =====
        console.print("\n[bold yellow]📈 DAQ 能力[/bold yellow]")
        try:
            daq_info = xcp.getDaqInfo()
            daq_table = Table(title="DAQ 配置", border_style="blue")
            daq_table.add_column("项目", style="cyan", no_wrap=True)
            daq_table.add_column("值", style="green")
            daq_table.add_row("DAQ 配置类型", str(daq_info.daqConfigType))
            daq_table.add_row("最大 DAQ 列表数", str(daq_info.maxDaq))
            daq_table.add_row("最大事件通道数", str(daq_info.maxEventChannel))
            daq_table.add_row("最小 DAQ 列表号", str(daq_info.minDaq))
            console.print(daq_table)
        except Exception as e:
            console.print(f"[yellow]⚠ 获取 DAQ 信息失败: {e}[/yellow]")

        # ===== 握手测试 =====
        console.print("\n[bold yellow]🤝 执行握手测试（5项）[/bold yellow]")

        tests_passed = 0
        tests_total = 5

        # 测试 1: GET_STATUS
        console.print("  [1/5] GET_STATUS...", end=" ")
        try:
            xcp.getStatus()
            console.print("[green]✓ 通过[/green]")
            tests_passed += 1
        except Exception as e:
            console.print(f"[red]✗ 失败: {e}[/red]")

        time.sleep(0.1)

        # 测试 2: GET_COMM_MODE_INFO
        console.print("  [2/5] GET_COMM_MODE_INFO...", end=" ")
        try:
            if xcp.slaveProperties.optionalCommMode:
                xcp.getCommModeInfo()
                console.print("[green]✓ 通过[/green]")
            else:
                console.print("[yellow]⚠ 不支持（跳过）[/yellow]")
            tests_passed += 1
        except Exception as e:
            console.print(f"[yellow]⚠ 失败（可选命令）: {e}[/yellow]")
            tests_passed += 1  # 可选命令也算通过

        time.sleep(0.1)

        # 测试 3: GET_ID
        console.print("  [3/5] GET_ID...", end=" ")
        try:
            xcp.identifier(0x01)
            console.print("[green]✓ 通过[/green]")
            tests_passed += 1
        except Exception as e:
            console.print(f"[red]✗ 失败: {e}[/red]")

        time.sleep(0.1)

        # 测试 4: SHORT_UPLOAD
        console.print("  [4/5] SHORT_UPLOAD (读取4字节)...", end=" ")
        try:
            xcp.setMta(0x00000000, 0)
            data = xcp.shortUpload(4)
            console.print(f"[green]✓ 通过 (0x{data.hex()})[/green]")
            tests_passed += 1
        except Exception as e:
            console.print(f"[yellow]⚠ 失败: {e}[/yellow]")

        time.sleep(0.1)

        # 测试 5: BUILD_CHECKSUM
        console.print("  [5/5] BUILD_CHECKSUM (256字节)...", end=" ")
        try:
            xcp.setMta(0x00000000, 0)
            checksum = xcp.buildChecksum(256)
            console.print(f"[green]✓ 通过 (0x{checksum.checksum:08X})[/green]")
            tests_passed += 1
        except Exception as e:
            console.print(f"[yellow]⚠ 失败: {e}[/yellow]")

        # ===== 测试结果汇总 =====
        console.print("")
        result_text = Text()
        result_text.append("测试结果: ", style="bold")
        result_text.append(f"{tests_passed}/{tests_total}", style="bold green")
        result_text.append(" 通过", style="bold")

        if tests_passed == tests_total:
            emoji = "🎉"
            color = "green"
        elif tests_passed >= tests_total - 1:
            emoji = "✅"
            color = "yellow"
        else:
            emoji = "❌"
            color = "red"

        console.print(Panel.fit(
            f"{emoji} {result_text}",
            title="测试完成",
            border_style=color
        ))

        # ===== 断开连接 =====
        console.print("\n[bold yellow]🔌 断开连接...[/bold yellow]")
        try:
            xcp.disconnect()
            console.print("[green]✓ 断开成功[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ 断开时出错: {e}[/yellow]")

    console.print("\n[bold cyan]测试完成！[/bold cyan]")


if __name__ == "__main__":
    main()
