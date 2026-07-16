import socket
import asyncio
import inspect
import random
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import argparse
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List, Protocol, runtime_checkable
from abc import ABC, abstractmethod
from datetime import datetime

@dataclass
class FileInfo:
    name: str
    size: int
    modified: datetime
    content: Optional[bytes] = None

@dataclass
class DirectoryInfo:
    files: List[FileInfo]
    dirs: List[str]

@dataclass
class FTPResponse:
    code: int
    message: str

    def encode(self) -> bytes:
        return f"{self.code} {self.message}\r\n".encode()

class IFileSystem(ABC):
    """Interface for file system operations."""
    @abstractmethod
    def get_dir_info(self, path: str) -> Optional[DirectoryInfo]:
        pass

    @abstractmethod
    def get_file_info(self, path: str) -> Optional[FileInfo]:
        pass

    @abstractmethod
    def store_file(self, path: str, content: bytes) -> None:
        pass

class IMockBehavior(ABC):
    @abstractmethod
    def should_return_error(self, command: str) -> bool:
        pass

    @abstractmethod
    def get_command_delay(self, command: str) -> float:
        pass

    @abstractmethod
    def log_message(self, message: str) -> None:
        pass

class IFTPCommandHandler(ABC):
    @abstractmethod
    async def handle_command(self, command: str, args: str) -> FTPResponse:
        pass

    @abstractmethod
    async def handle_data_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        pass

class VirtualFileSystem(IFileSystem):
    def __init__(self):
        self.fs = {
            '/': DirectoryInfo(
                files=[
                    FileInfo('README.txt', 1024, datetime(2024,1,1), b'Welcome to FTP server'),
                    FileInfo('data.bin', 2048, datetime(2024,1,2), b'Binary data')
                ],
                dirs=['docs', 'images']
            ),
            '/docs': DirectoryInfo(
                files=[
                    FileInfo('manual.pdf', 4096, datetime(2024,1,3), b'PDF content'),
                    FileInfo('specs.doc', 3072, datetime(2024,1,4), b'Doc content')
                ],
                dirs=['specs']
            ),
            '/docs/specs': DirectoryInfo(
                files=[
                    FileInfo('api.md', 512, datetime(2024,1,5), b'API docs'),
                ],
                dirs=[]
            ),
            '/images': DirectoryInfo(
                files=[
                    FileInfo('photo.jpg', 8192, datetime(2024,1,6), b'JPEG data'),
                    FileInfo('icon.png', 1024, datetime(2024,1,7), b'PNG data')
                ],
                dirs=['thumbnails']
            ),
            '/images/thumbnails': DirectoryInfo(
                files=[
                    FileInfo('thumb1.jpg', 256, datetime(2024,1,8), b'Small JPEG'),
                ],
                dirs=[]
            )
        }

    def get_dir_info(self, path: str) -> Optional[DirectoryInfo]:
        return self.fs.get(path)

    def get_file_info(self, path: str) -> Optional[FileInfo]:
        dirname = '/'.join(path.split('/')[:-1]) or '/'
        filename = path.split('/')[-1]
        dir_info = self.get_dir_info(dirname)
        if dir_info:
            for file in dir_info.files:
                if file.name == filename:
                    return file
        return None

    def store_file(self, path: str, content: bytes) -> None:
        dirname = '/'.join(path.split('/')[:-1]) or '/'
        filename = path.split('/')[-1]
        dir_info = self.get_dir_info(dirname)
        if dir_info:
            new_file = FileInfo(
                name=filename,
                size=len(content),
                modified=datetime.now(),
                content=content
            )
            dir_info.files.append(new_file)

logger = logging.getLogger("mock_ftp_server")

class MockBehavior(IMockBehavior):
    def __init__(self):
        self.error_settings = {}
        self.delay_settings = {}
        self.setup_logging()

    def setup_logging(self):
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
        
        # Avoid duplicate handlers
        if not logger.handlers:
            # Console Handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    def should_return_error(self, command: str) -> bool:
        return self.error_settings.get(command, tk.BooleanVar()).get()

    def get_command_delay(self, command: str) -> float:
        spinbox = self.delay_settings.get(command)
        if spinbox:
            try:
                return float(spinbox.get())
            except ValueError:
                return 0
        return 0

    def log_message(self, message: str) -> None:
        logger.info(message)

    def set_error_settings(self, command: str, var: tk.BooleanVar) -> None:
        self.error_settings[command] = var

    def set_delay_settings(self, command: str, spinbox: tk.Spinbox) -> None:
        self.delay_settings[command] = spinbox


class MockServerGUI:
    def __init__(self, mock_behavior: MockBehavior, server: 'FTPMockServer'):
        self.mock_behavior = mock_behavior
        self.server = server
        self.root = None
        self.status_label = None
        self.start_btn = None
        self.stop_btn = None

    def run(self):
        self.root = tk.Tk()
        self.root.title("FTP Mock Server")
        self.root.geometry("380x520")

        # VSCode/Zed-like Dark Theme Palette
        bg_dark = "#181818"      # Sidebar/Settings background
        bg_editor = "#1e1e1e"    # Input elements background
        bg_header = "#2d2d2d"    # Header background
        bg_hover = "#3c3c3c"     # Hover background
        fg_main = "#cccccc"      # Main text foreground
        accent_color = "#007acc" # VSCode Blue accent
        border_color = "#303030" # Flat borders

        self.root.configure(bg=bg_dark)

        # Detect platform for typography fallback
        windowing_system = self.root.tk.call('tk', 'windowingsystem')
        if windowing_system == 'win32':
            font_family_ui = "Segoe UI"
        elif windowing_system == 'aqua':
            font_family_ui = "SF Pro Text"
        else:
            font_family_ui = "DejaVu Sans"

        font_spec_ui = (font_family_ui, 10)
        font_spec_ui_bold = (font_family_ui, 10, "bold")

        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        # Configure styles
        style.configure('.', background=bg_dark, foreground=fg_main, font=font_spec_ui)
        style.configure('TFrame', background=bg_dark)
        
        # LabelFrame with thin border and clean padding
        style.configure('TLabelframe', background=bg_dark, foreground=fg_main, bordercolor=border_color, lightcolor=border_color, darkcolor=border_color, borderwidth=1)
        style.configure('TLabelframe.Label', background=bg_dark, foreground=accent_color, font=font_spec_ui_bold)
        
        style.configure('TLabel', background=bg_dark, foreground=fg_main)
        
        # Checkbutton styling
        style.configure('TCheckbutton', background=bg_dark, foreground=fg_main, focuscolor=accent_color)
        style.map('TCheckbutton',
                  background=[('active', bg_dark)],
                  indicatorcolor=[('selected', accent_color), ('!selected', bg_dark)],
                  foreground=[('active', fg_main)])

        # Flat Button styling
        style.configure('TButton', background=bg_header, foreground=fg_main, bordercolor=border_color, lightcolor=border_color, darkcolor=border_color, borderwidth=1, relief="flat", padding=(10, 4))
        style.map('TButton',
                  background=[('pressed', accent_color), ('active', bg_hover), ('disabled', bg_dark)],
                  foreground=[('pressed', '#ffffff'), ('active', fg_main), ('disabled', '#555555')],
                  bordercolor=[('focus', accent_color), ('active', border_color), ('disabled', border_color)])

        # Spinbox styling
        style.configure('TSpinbox', fieldbackground=bg_editor, foreground=fg_main, background=bg_header, arrowcolor=fg_main, bordercolor=border_color, lightcolor=border_color, darkcolor=border_color, borderwidth=1)
        style.map('TSpinbox',
                  fieldbackground=[('focus', bg_editor)],
                  bordercolor=[('focus', accent_color)])

        # Server Control Frame
        control_frame = ttk.LabelFrame(self.root, text="Server Control")
        control_frame.pack(fill=tk.X, padx=15, pady=(15, 0))
        
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(2, weight=1)

        # Status Label (dynamic color depending on state)
        self.status_label = ttk.Label(control_frame, text="Status: RUNNING", font=font_spec_ui_bold, foreground="#3794ff")
        self.status_label.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        self.start_btn = ttk.Button(control_frame, text="Start", command=self.click_start)
        self.start_btn.grid(row=0, column=1, padx=4, pady=8, sticky="ew")
        self.start_btn.state(['disabled']) # Running at start

        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.click_stop)
        self.stop_btn.grid(row=0, column=2, padx=4, pady=8, sticky="ew")

        # TCP RST Disconnect Button
        self.rst_btn = ttk.Button(control_frame, text="Force TCP RST Disconnect", command=self.click_rst)
        self.rst_btn.grid(row=1, column=0, columnspan=3, padx=8, pady=8, sticky="ew")

        # Settings Frame (Packed directly to root, taking remaining space)
        settings_frame = ttk.LabelFrame(self.root, text="Command Settings")
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Configure columns for setting frame to distribute space nicely
        settings_frame.columnconfigure(0, weight=2)
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(2, weight=1)

        # Headers
        ttk.Label(settings_frame, text="Command", font=font_spec_ui_bold).grid(row=0, column=0, padx=8, pady=8, sticky="w")
        ttk.Label(settings_frame, text="Force Error", font=font_spec_ui_bold).grid(row=0, column=1, padx=8, pady=8)
        ttk.Label(settings_frame, text="Delay (s)", font=font_spec_ui_bold).grid(row=0, column=2, padx=8, pady=8)

        commands = ["USER", "PASS", "PWD", "TYPE", "PASV", "LIST", "CWD", "QUIT", "STOR"]
        for i, cmd in enumerate(commands, start=1):
            ttk.Label(settings_frame, text=cmd, font=font_spec_ui).grid(row=i, column=0, padx=8, pady=4, sticky="w")

            var = tk.BooleanVar()
            self.mock_behavior.set_error_settings(cmd, var)
            ttk.Checkbutton(settings_frame, variable=var).grid(row=i, column=1, padx=8, pady=4)

            spinbox = ttk.Spinbox(settings_frame, from_=0, to=10, increment=0.1, width=8)
            spinbox.set(0)
            spinbox.grid(row=i, column=2, padx=8, pady=4)
            self.mock_behavior.set_delay_settings(cmd, spinbox)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def click_start(self):
        if not self.server.running:
            self.server.start()
            self.status_label.config(text="Status: RUNNING", foreground="#3794ff")
            self.start_btn.state(['disabled'])
            self.stop_btn.state(['!disabled'])

    def click_stop(self):
        if self.server.running:
            self.server.stop()
            self.status_label.config(text="Status: STOPPED", foreground="#e51400")
            self.start_btn.state(['!disabled'])
            self.stop_btn.state(['disabled'])

    def click_rst(self):
        self.server.force_rst_disconnect()

    def on_close(self):
        if self.root:
            self.root.destroy()
            self.root = None



class FTPCommandHandler(IFTPCommandHandler):
    def __init__(self, host: str, data_port: int, file_system: IFileSystem, mock_behavior: IMockBehavior):
        self.current_directory = "/"
        self.host = host
        self.data_port = data_port
        self.data_server = None
        self.vfs = file_system
        self.mock_behavior = mock_behavior
        self.store_mode = False
        self.pending_store_filename = None

    def _format_directory_entry(self, name: str, is_dir: bool = False) -> str:
        if is_dir:
            return f"drwxr-xr-x 2 owner group 4096 {datetime.now().strftime('%b %d %H:%M')} {name}"

        path = self.current_directory
        if not path.endswith('/'):
            path += '/'
        path += name

        file_info = self.vfs.get_file_info(path)
        if file_info:
            return f"-rw-r--r-- 1 owner group {file_info.size} {file_info.modified.strftime('%b %d %H:%M')} {name}"
        return f"-rw-r--r-- 1 owner group 0 {datetime.now().strftime('%b %d %H:%M')} {name}"

    def get_directory_listing(self, path: str) -> str:
        result = [
            "drwxrwxrwx 3 owner group 4096 Jan 01 18:00 .",
            "drwxrwxrwx 3 owner group 4096 Jan 01 18:00 .."
        ]

        dir_info = self.vfs.get_dir_info(path)
        if dir_info:
            for dirname in dir_info.dirs:
                result.append(self._format_directory_entry(dirname, is_dir=True))
            for file in dir_info.files:
                result.append(self._format_directory_entry(file.name))

        return '\r\n'.join(result) + '\r\n'

    async def _setup_passive_mode(self) -> FTPResponse:
        if self.mock_behavior.should_return_error("PASV"):
            return FTPResponse(500, "PASV command failed")

        delay = self.mock_behavior.get_command_delay("PASV")
        if delay > 0:
            await asyncio.sleep(delay)

        if self.data_server:
            self.data_server.close()

        random_port = random.randint(50000, 50100)
        self.data_server = await asyncio.start_server(
            self.handle_data_connection,
            self.host,
            random_port
        )

        h1, h2, h3, h4 = self.host.split('.')
        p1, p2 = divmod(random_port, 256)
        return FTPResponse(227, f"Entering Passive Mode ({h1},{h2},{h3},{h4},{p1},{p2})")

    async def _handle_cwd_command(self, path: str) -> FTPResponse:
        if self.mock_behavior.should_return_error("CWD"):
            return FTPResponse(550, "CWD command failed")

        delay = self.mock_behavior.get_command_delay("CWD")
        if delay > 0:
            await asyncio.sleep(delay)

        if path == "..":
            if self.current_directory == "/":
                new_path = "/"
            else:
                parts = self.current_directory.rstrip('/').split('/')
                new_path = '/'.join(parts[:-1])
                if not new_path:
                    new_path = "/"
        elif path.startswith('/'):
            new_path = path
        else:
            if self.current_directory.endswith('/'):
                new_path = self.current_directory + path
            else:
                new_path = self.current_directory + '/' + path

        while '//' in new_path:
            new_path = new_path.replace('//', '/')
        if not new_path.startswith('/'):
            new_path = '/' + new_path
        if new_path != '/' and new_path.endswith('/'):
            new_path = new_path[:-1]

        if self.vfs.get_dir_info(new_path):
            self.current_directory = new_path
            return FTPResponse(250, "Directory successfully changed.")

        return FTPResponse(550, "Directory not found.")

    async def _handle_stor_command(self, filename: str) -> FTPResponse:
        if self.mock_behavior.should_return_error("STOR"):
            return FTPResponse(550, "STOR command failed")

        delay = self.mock_behavior.get_command_delay("STOR")
        if delay > 0:
            await asyncio.sleep(delay)

        if not self.data_server:
            return FTPResponse(425, "Use PASV first")

        self.store_mode = True
        self.pending_store_filename = filename
        return FTPResponse(150, "Ok to send data")

    async def _handle_list_command(self) -> FTPResponse:
        if self.mock_behavior.should_return_error("LIST"):
            return FTPResponse(500, "LIST command failed")

        delay = self.mock_behavior.get_command_delay("LIST")
        if delay > 0:
            await asyncio.sleep(delay)

        if not self.data_server:
            return FTPResponse(425, "Use PASV first")
        self.pending_data = self.get_directory_listing(self.current_directory)
        return FTPResponse(150, "Opening ASCII mode data connection for file list")

    async def _handle_quit_command(self) -> FTPResponse:
        if self.mock_behavior.should_return_error("QUIT"):
            return FTPResponse(500, "QUIT command failed")

        delay = self.mock_behavior.get_command_delay("QUIT")
        if delay > 0:
            await asyncio.sleep(delay)

        if self.data_server:
            self.data_server.close()
        return FTPResponse(221, "Goodbye")

    async def handle_command(self, command: str, args: str) -> FTPResponse:
        command = command.upper()
        self.mock_behavior.log_message(f"Received command: {command} {args}")

        if self.mock_behavior.should_return_error(command):
            return FTPResponse(500, f"{command} command failed")

        delay = self.mock_behavior.get_command_delay(command)
        if delay > 0:
            await asyncio.sleep(delay)

        command_handlers = {
            "USER": lambda: FTPResponse(331, "User name okay, need password"),
            "PASS": lambda: FTPResponse(230, "User logged in"),
            "PWD":  lambda: FTPResponse(257, f"\"{self.current_directory}\" is current directory"),
            "TYPE": lambda: FTPResponse(200, "Type set to I"),
            "PASV": self._setup_passive_mode,
            "LIST": self._handle_list_command,
            "CWD": self._handle_cwd_command,
            "STOR": self._handle_stor_command,
            "QUIT": self._handle_quit_command,
        }

        handler = command_handlers.get(command)
        if handler:
            if inspect.iscoroutinefunction(handler):
                if command == "CWD":
                    response = await handler(args)
                elif command == "STOR":
                    response = await handler(args)
                else:
                    response = await handler()
            else:
                response = handler()
            self.mock_behavior.log_message(f"Sending response: {response.code} {response.message}")
            return response

        response = FTPResponse(500, "Unknown command")
        self.mock_behavior.log_message(f"Sending response: {response.code} {response.message}")
        return response

    async def handle_data_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        if self.store_mode:
            data = await reader.read()
            path = self.current_directory
            if not path.endswith('/'):
                path += '/'
            path += self.pending_store_filename
            self.vfs.store_file(path, data)
            msg = f"Stored {len(data)} bytes to file {path}"
            logger.info(msg)
            self.store_mode = False
            self.pending_store_filename = None
            writer.close()
            await writer.wait_closed()
        elif hasattr(self, 'pending_data'):
            writer.write(self.pending_data.encode())
            await writer.drain()
            delattr(self, 'pending_data')
            writer.close()
            await writer.wait_closed()

class FTPMockServer:
    def __init__(self, host='127.0.0.1', port=8021):
        self.host = host
        self.port = port
        self.running = False
        self.data_port = port
        self.server = None
        self.loop = None
        self.server_thread = None
        self.active_clients = set()

        self.mock_behavior = MockBehavior()
        self.file_system = VirtualFileSystem()
        self.command_handler = FTPCommandHandler(
            self.host,
            self.data_port,
            self.file_system,
            self.mock_behavior
        )

        self.gui = MockServerGUI(self.mock_behavior, server=self)

    def start(self):
        self.running = True
        self.loop = asyncio.new_event_loop()
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

    def _run_server(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start_async_server())

    async def _start_async_server(self):
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        msg = f"FTP Mock Server running on {self.host}:{self.port}"
        logger.info(msg)

        async with self.server:
            try:
                await self.server.serve_forever()
            except asyncio.CancelledError:
                pass

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.active_clients.add(writer)
        addr = writer.get_extra_info('peername')
        msg = f"Client connected from {addr}"
        logger.info(msg)

        try:
            writer.write(FTPResponse(220, "Welcome to FTP Mock Server").encode())
            await writer.drain()

            while True:
                try:
                    data = (await reader.read(1024)).decode().strip()
                    if not data:
                        break

                    logger.info(f"> {data}")
                    command = data.split(' ')[0]
                    args = data[len(command):].strip()

                    response = await self.command_handler.handle_command(command, args)
                    writer.write(response.encode())
                    logger.info(f"< {response.code} {response.message}")
                    await writer.drain()

                    if response.code == 150:  # For LIST or STOR command
                        writer.write(FTPResponse(226, "Transfer complete").encode())
                        await writer.drain()

                    if command.upper() == "QUIT":
                        break

                except Exception as e:
                    msg = f"Error handling client: {e}"
                    logger.error(msg)
                    break
        finally:
            self.active_clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            msg = f"Client disconnected from {addr}"
            logger.info(msg)

    def force_rst_disconnect(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self._async_force_rst_disconnect)

    def _async_force_rst_disconnect(self):
        import struct
        clients = list(self.active_clients)
        if not clients:
            logger.info("No active clients to disconnect.")
            return
        logger.info(f"Forcing TCP RST disconnect for {len(clients)} client(s)...")
        for writer in clients:
            try:
                sock = writer.get_extra_info('socket')
                if sock:
                    # SO_LINGER onoff=1, l_linger=0 forces TCP RST on close
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                writer.close()
            except Exception as e:
                logger.error(f"Error during RST disconnect: {e}")

    def stop(self):
        self.running = False
        if self.server:
            self.server.close()
            self.server = None
        if self.loop:
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop = None
        if self.server_thread:
            self.server_thread.join(timeout=1.0)
            self.server_thread = None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='FTP Mock Server')
    parser.add_argument('--port', type=int, default=8021, help='Port number to listen on')
    args = parser.parse_args()

    server = FTPMockServer(port=args.port)
    server.start()
    try:
        server.gui.run()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        server.stop()
