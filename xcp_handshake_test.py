#!/usr/bin/env python
"""XCP 握手测试工具 - 用于测试与下位机的连接和基本通信。"""

import sys
import time
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog

from pyxcp.cmdline import ArgumentParser
from pyxcp import __version__ as pyxcp_version


class XcpHandshakeTest:
    """XCP 握手测试主类。"""

    def __init__(self, root):
        self.root = root
        self.root.title(f"XCP 握手测试工具 v1.0 (pyXCP {pyxcp_version})")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        self.xcp = None
        self.connected = False
        self._lock = threading.Lock()

        self._build_ui()
        self._log("系统就绪，请配置连接参数后点击「连接」")

    def _build_ui(self):
        """构建用户界面。"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === 连接配置区域 ===
        conn_frame = ttk.LabelFrame(main_frame, text="连接配置", padding="10")
        conn_frame.pack(fill=tk.X, pady=(0, 10))

        # 传输方式选择
        ttk.Label(conn_frame, text="传输方式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.transport_var = tk.StringVar(value="eth")
        transport_combo = ttk.Combobox(
            conn_frame,
            textvariable=self.transport_var,
            values=["eth", "sxi", "can"],
            state="readonly",
            width=10
        )
        transport_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 20), pady=5)
        transport_combo.bind("<<ComboboxSelected>>", self._on_transport_changed)

        # 以太网配置
        self.eth_frame = ttk.Frame(conn_frame)
        self.eth_frame.grid(row=0, column=2, columnspan=4, sticky=tk.W)

        ttk.Label(self.eth_frame, text="IP地址:").pack(side=tk.LEFT)
        self.ip_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(self.eth_frame, textvariable=self.ip_var, width=15).pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(self.eth_frame, text="端口:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="5555")
        ttk.Entry(self.eth_frame, textvariable=self.port_var, width=8).pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(self.eth_frame, text="协议:").pack(side=tk.LEFT)
        self.eth_proto_var = tk.StringVar(value="TCP")
        ttk.Combobox(
            self.eth_frame,
            textvariable=self.eth_proto_var,
            values=["TCP", "UDP"],
            state="readonly",
            width=6
        ).pack(side=tk.LEFT, padx=(5, 0))

        # 串口配置
        self.sxi_frame = ttk.Frame(conn_frame)
        ttk.Label(self.sxi_frame, text="串口号:").pack(side=tk.LEFT)
        self.serial_port_var = tk.StringVar(value="COM1")
        ttk.Entry(self.sxi_frame, textvariable=self.serial_port_var, width=10).pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(self.sxi_frame, text="波特率:").pack(side=tk.LEFT)
        self.baudrate_var = tk.StringVar(value="115200")
        ttk.Combobox(
            self.sxi_frame,
            textvariable=self.baudrate_var,
            values=["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"],
            state="readonly",
            width=10
        ).pack(side=tk.LEFT, padx=(5, 0))

        # CAN配置
        self.can_frame = ttk.Frame(conn_frame)
        ttk.Label(self.can_frame, text="接口:").pack(side=tk.LEFT)
        self.can_interface_var = tk.StringVar(value="socketcan")
        ttk.Entry(self.can_frame, textvariable=self.can_interface_var, width=10).pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(self.can_frame, text="通道:").pack(side=tk.LEFT)
        self.can_channel_var = tk.StringVar(value="can0")
        ttk.Entry(self.can_frame, textvariable=self.can_channel_var, width=10).pack(side=tk.LEFT, padx=(5, 0))

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.connect_btn = ttk.Button(btn_frame, text="🔌 连接", command=self._on_connect, width=15)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.disconnect_btn = ttk.Button(btn_frame, text="⏹ 断开", command=self._on_disconnect, width=15, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.handshake_btn = ttk.Button(btn_frame, text="🤝 握手测试", command=self._on_handshake, width=15, state=tk.DISABLED)
        self.handshake_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.read_btn = ttk.Button(btn_frame, text="📖 读内存测试", command=self._on_read_test, width=15, state=tk.DISABLED)
        self.read_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.clear_btn = ttk.Button(btn_frame, text="🧹 清空日志", command=self._clear_log, width=15)
        self.clear_btn.pack(side=tk.RIGHT)

        # === 测试结果区域 ===
        result_frame = ttk.LabelFrame(main_frame, text="从设备信息", padding="10")
        result_frame.pack(fill=tk.X, pady=(0, 10))

        self.info_text = tk.Text(result_frame, height=8, wrap=tk.WORD, font=("Consolas", 10))
        info_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scroll.set)
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # === 日志区域 ===
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            height=15
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))

        self._on_transport_changed(None)

    def _on_transport_changed(self, event):
        """传输方式改变时更新界面。"""
        transport = self.transport_var.get()
        self.eth_frame.grid_remove()
        self.sxi_frame.grid_remove()
        self.can_frame.grid_remove()

        if transport == "eth":
            self.eth_frame.grid(row=0, column=2, columnspan=4, sticky=tk.W)
        elif transport == "sxi":
            self.sxi_frame.grid(row=0, column=2, columnspan=4, sticky=tk.W)
        elif transport == "can":
            self.can_frame.grid(row=0, column=2, columnspan=4, sticky=tk.W)

    def _log(self, message, level="INFO"):
        """添加日志。"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        color_map = {
            "INFO": "black",
            "SUCCESS": "green",
            "ERROR": "red",
            "WARN": "orange",
            "DEBUG": "gray"
        }
        color = color_map.get(level, "black")

        self.log_text.insert(tk.END, f"[{timestamp}] [{level}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _clear_log(self):
        """清空日志。"""
        self.log_text.delete("1.0", tk.END)

    def _set_status(self, text):
        """设置状态栏文字。"""
        self.status_var.set(text)
        self.root.update_idletasks()

    def _set_buttons_state(self, connected):
        """根据连接状态设置按钮可用性。"""
        if connected:
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.handshake_btn.config(state=tk.NORMAL)
            self.read_btn.config(state=tk.NORMAL)
        else:
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.handshake_btn.config(state=tk.DISABLED)
            self.read_btn.config(state=tk.DISABLED)

    def _build_config_args(self):
        """根据界面配置构建命令行参数。"""
        transport = self.transport_var.get()
        args = ["xcp_test"]

        if transport == "eth":
            args.extend(["--transport", "eth"])
            args.extend(["--host", self.ip_var.get()])
            args.extend(["--port", self.port_var.get()])
            proto = self.eth_proto_var.get().lower()
            args.extend(["--protocol", proto])
        elif transport == "sxi":
            args.extend(["--transport", "sxi"])
            args.extend(["--port", self.serial_port_var.get()])
            args.extend(["--baudrate", self.baudrate_var.get()])
        elif transport == "can":
            args.extend(["--transport", "can"])
            args.extend(["--interface", self.can_interface_var.get()])
            args.extend(["--channel", self.can_channel_var.get()])

        return args

    def _on_connect(self):
        """连接按钮点击事件。"""
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self):
        """连接工作线程。"""
        with self._lock:
            try:
                self._set_status("正在连接...")
                self._log("开始建立 XCP 连接...")

                args = self._build_config_args()
                self._log(f"连接参数: {' '.join(args[1:])}")

                ap = ArgumentParser(description="XCP 握手测试")
                self.xcp = ap.run().__enter__()

                self._log("正在执行 CONNECT 命令...", "DEBUG")
                self.xcp.connect()
                self.connected = True

                self._log("✅ 连接成功！", "SUCCESS")
                self._set_status("已连接")

                # 获取从设备信息
                self._get_slave_info()

                self.root.after(0, lambda: self._set_buttons_state(True))

            except Exception as e:
                self._log(f"❌ 连接失败: {e}", "ERROR")
                self._set_status("连接失败")
                self.xcp = None
                self.connected = False
                messagebox.showerror("连接失败", str(e))

    def _get_slave_info(self):
        """获取从设备信息并显示。"""
        try:
            self._log("正在获取从设备信息...")

            info_lines = []
            info_lines.append("=" * 60)
            info_lines.append("  从设备基本信息")
            info_lines.append("=" * 60)

            # 获取标识符
            try:
                for id_type, id_name in [
                    (0x00, "ASCII文本"),
                    (0x01, "文件名"),
                    (0x02, "文件和路径"),
                    (0x05, "EPK"),
                    (0x06, "ECU"),
                    (0x07, "SYSID"),
                ]:
                    try:
                        identifier = self.xcp.identifier(id_type)
                        if identifier:
                            decoded = identifier.decode("utf-8", errors="replace").strip("\x00").strip()
                            info_lines.append(f"  {id_name:12s}: {decoded}")
                    except Exception:
                        pass
            except Exception as e:
                self._log(f"获取标识符失败: {e}", "WARN")

            info_lines.append("")
            info_lines.append("=" * 60)
            info_lines.append("  Slave Properties")
            info_lines.append("=" * 60)

            props = self.xcp.slaveProperties
            for key, value in sorted(props.items()):
                info_lines.append(f"  {key:30s}: {value}")

            info_lines.append("")
            info_lines.append("=" * 60)
            info_lines.append("  状态信息")
            info_lines.append("=" * 60)

            try:
                status = self.xcp.getStatus()
                info_lines.append(f"  当前会话状态       : {status.currentSessionStatus}")
                info_lines.append(f"  资源保护状态       : {status.resourceProtectionStatus}")
                info_lines.append(f"  会话配置          : {status.sessionConfiguration}")
            except Exception as e:
                self._log(f"获取状态失败: {e}", "WARN")

            # DAQ能力
            info_lines.append("")
            info_lines.append("=" * 60)
            info_lines.append("  DAQ 能力")
            info_lines.append("=" * 60)

            try:
                daq_info = self.xcp.getDaqInfo()
                info_lines.append(f"  DAQ配置类型        : {daq_info.daqConfigType}")
                info_lines.append(f"  最大DAQ列表数      : {daq_info.maxDaq}")
                info_lines.append(f"  最大事件通道数     : {daq_info.maxEventChannel}")
                info_lines.append(f"  最小DAQ列表号      : {daq_info.minDaq}")
            except Exception as e:
                info_lines.append(f"  (DAQ不支持: {e})")

            info_text = "\n".join(info_lines)

            def update_info():
                self.info_text.delete("1.0", tk.END)
                self.info_text.insert("1.0", info_text)

            self.root.after(0, update_info)
            self._log("从设备信息获取完成", "SUCCESS")

        except Exception as e:
            self._log(f"获取从设备信息时出错: {e}", "ERROR")

    def _on_disconnect(self):
        """断开按钮点击事件。"""
        threading.Thread(target=self._disconnect_worker, daemon=True).start()

    def _disconnect_worker(self):
        """断开工作线程。"""
        with self._lock:
            try:
                self._set_status("正在断开...")
                self._log("正在断开连接...")

                if self.xcp and self.connected:
                    self.xcp.disconnect()
                    self._log("✅ 断开成功", "SUCCESS")

            except Exception as e:
                self._log(f"断开时出错: {e}", "WARN")
            finally:
                if self.xcp:
                    try:
                        self.xcp.__exit__(None, None, None)
                    except Exception:
                        pass
                self.xcp = None
                self.connected = False
                self._set_status("已断开")
                self.root.after(0, lambda: self._set_buttons_state(False))

    def _on_handshake(self):
        """握手测试按钮点击事件。"""
        threading.Thread(target=self._handshake_worker, daemon=True).start()

    def _handshake_worker(self):
        """握手测试工作线程。"""
        with self._lock:
            if not self.connected or not self.xcp:
                return

            try:
                self._set_status("正在进行握手测试...")
                self._log("=" * 50)
                self._log("开始 XCP 握手测试")
                self._log("=" * 50)

                # 测试1: GET_STATUS
                self._log("测试 1/5: GET_STATUS...")
                status = self.xcp.getStatus()
                self._log(f"  ✓ 状态: {status.currentSessionStatus}", "SUCCESS")

                time.sleep(0.1)

                # 测试2: GET_COMM_MODE_INFO
                self._log("测试 2/5: GET_COMM_MODE_INFO...")
                try:
                    comm_mode = self.xcp.getCommModeInfo()
                    self._log(f"  ✓ 通信模式: {comm_mode}", "SUCCESS")
                except Exception as e:
                    self._log(f"  ⚠ 可选命令不支持: {e}", "WARN")

                time.sleep(0.1)

                # 测试3: GET_ID
                self._log("测试 3/5: GET_ID...")
                try:
                    identifier = self.xcp.identifier(0x01)
                    decoded = identifier.decode("utf-8", errors="replace").strip("\x00").strip()
                    self._log(f"  ✓ 从设备ID: {decoded}", "SUCCESS")
                except Exception as e:
                    self._log(f"  ⚠ 获取ID失败: {e}", "WARN")

                time.sleep(0.1)

                # 测试4: 短上传测试
                self._log("测试 4/5: SHORT_UPLOAD 读取测试...")
                try:
                    self.xcp.setMta(0x00000000, 0)
                    data = self.xcp.shortUpload(4)
                    self._log(f"  ✓ 读取4字节: {data.hex()}", "SUCCESS")
                except Exception as e:
                    self._log(f"  ⚠ 读取测试失败: {e}", "WARN")

                time.sleep(0.1)

                # 测试5: 校验和测试
                self._log("测试 5/5: BUILD_CHECKSUM...")
                try:
                    self.xcp.setMta(0x00000000, 0)
                    checksum = self.xcp.buildChecksum(256)
                    self._log(f"  ✓ 校验和: 0x{checksum.checksum:08X}", "SUCCESS")
                except Exception as e:
                    self._log(f"  ⚠ 校验和测试失败: {e}", "WARN")

                self._log("=" * 50)
                self._log("🎉 握手测试完成！", "SUCCESS")
                self._log("=" * 50)
                self._set_status("测试完成")

            except Exception as e:
                self._log(f"❌ 握手测试失败: {e}", "ERROR")
                self._set_status("测试失败")

    def _on_read_test(self):
        """读内存测试。"""
        result = simpledialog.askstring(
            "读内存测试",
            "请输入读取地址和长度（格式: 地址,长度，如 0x00000000,16）:",
            parent=self.root
        )
        if not result:
            return

        try:
            parts = result.split(",")
            if len(parts) != 2:
                raise ValueError("格式错误")
            addr = int(parts[0].strip(), 0)
            length = int(parts[1].strip(), 0)

            threading.Thread(target=lambda: self._read_test_worker(addr, length), daemon=True).start()
        except Exception as e:
            messagebox.showerror("参数错误", f"输入格式错误: {e}\n请使用格式: 地址,长度")

    def _read_test_worker(self, addr, length):
        """读内存测试工作线程。"""
        with self._lock:
            if not self.connected or not self.xcp:
                return

            try:
                self._set_status("正在读取内存...")
                self._log(f"读取内存: 地址=0x{addr:08X}, 长度={length}字节")

                self.xcp.setMta(addr, 0)
                data = self.xcp.upload(length)

                hex_str = data.hex().upper()
                hex_display = " ".join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)])

                self._log(f"读取成功:", "SUCCESS")
                self._log(f"  HEX: {hex_display}")

                # 尝试解析为不同类型
                if length >= 4:
                    import struct
                    u32 = struct.unpack("<I", data[:4])[0]
                    s32 = struct.unpack("<i", data[:4])[0]
                    f32 = struct.unpack("<f", data[:4])[0]
                    self._log(f"  uint32 LE: {u32}")
                    self._log(f"  int32  LE: {s32}")
                    self._log(f"  float  LE: {f32}")

                self._set_status("读取完成")

            except Exception as e:
                self._log(f"读取失败: {e}", "ERROR")
                self._set_status("读取失败")

    def on_close(self):
        """窗口关闭事件。"""
        if self.connected and self.xcp:
            try:
                self.xcp.disconnect()
                self.xcp.__exit__(None, None, None)
            except Exception:
                pass
        self.root.destroy()


def main():
    """主函数。"""
    root = tk.Tk()

    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    app = XcpHandshakeTest(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)

    try:
        import tkinter.simpledialog
    except ImportError:
        pass

    root.mainloop()


if __name__ == "__main__":
    main()
