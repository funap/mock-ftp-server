import socket
import asyncio
import random
import tkinter as tk
import threading
import queue
from dataclasses import dataclass
from typing import Optional, Dict, List
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

class VirtualFileSystem:
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

    def store_file(self, path: str, content: bytes):
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

class FTPCommandHandler:
    def __init__(self, current_directory: str, host: str, data_port: int):
        self.current_directory = current_directory
        self.host = host
        self.data_port = data_port
        self.data_server = None
        self.vfs = VirtualFileSystem()
        self.error_settings = {}
        self.delay_settings = {}
        self.log_queue = queue.Queue()
        self.store_mode = False
        self.pending_store_filename = None

        self.gui_thread = threading.Thread(target=self.run_gui)
        self.gui_thread.daemon = True
        self.gui_thread.start()

    def run_gui(self):
        self.root = tk.Tk()
        self.root.title("FTP Mock Server Settings")

        settings_frame = tk.Frame(self.root)
        settings_frame.pack(fill="x", padx=10, pady=5)

        commands = ["USER", "PASS", "PWD", "TYPE", "PASV", "LIST", "CWD", "QUIT", "STOR"]

        for cmd in commands:
            cmd_frame = tk.Frame(settings_frame)
            cmd_frame.pack(fill="x", anchor="w")

            var = tk.BooleanVar()
            self.error_settings[cmd] = var
            tk.Checkbutton(cmd_frame, text=f"{cmd} Error", variable=var).pack(side=tk.LEFT)

            tk.Label(cmd_frame, text="Delay:").pack(side=tk.LEFT, padx=(10,0))
            spinbox = tk.Spinbox(cmd_frame, from_=0, to=10, increment=0.1, width=5)
            spinbox.pack(side=tk.LEFT)
            self.delay_settings[cmd] = spinbox

        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        self.root.mainloop()

    def log_message(self, message: str):
        self.log_queue.put(message)

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
        if self.should_return_error("PASV"):
            return FTPResponse(500, "PASV command failed")

        delay = self.get_command_delay("PASV")
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
        if self.should_return_error("CWD"):
            return FTPResponse(550, "CWD command failed")

        delay = self.get_command_delay("CWD")
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
        if self.should_return_error("STOR"):
            return FTPResponse(550, "STOR command failed")

        delay = self.get_command_delay("STOR")
        if delay > 0:
            await asyncio.sleep(delay)

        if not self.data_server:
            return FTPResponse(425, "Use PASV first")

        self.store_mode = True
        self.pending_store_filename = filename
        return FTPResponse(150, "Ok to send data")

    async def handle_command(self, command: str, args: str) -> FTPResponse:
        command = command.upper()
        self.log_message(f"Received command: {command} {args}")

        if self.should_return_error(command):
            return FTPResponse(500, f"{command} command failed")

        delay = self.get_command_delay(command)
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
            "QUIT": self._handle_quit_command
        }

        handler = command_handlers.get(command)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                if command == "CWD":
                    response = await handler(args)
                elif command == "STOR":
                    response = await handler(args)
                else:
                    response = await handler()
            else:
                response = handler()
            self.log_message(f"Sending response: {response.code} {response.message}")
            return response
        return FTPResponse(500, "Unknown command")

    async def _handle_list_command(self) -> FTPResponse:
        if self.should_return_error("LIST"):
            return FTPResponse(500, "LIST command failed")

        delay = self.get_command_delay("LIST")
        if delay > 0:
            await asyncio.sleep(delay)

        if not self.data_server:
            return FTPResponse(425, "Use PASV first")
        self.pending_data = self.get_directory_listing(self.current_directory)
        return FTPResponse(150, "Opening ASCII mode data connection for file list")

    async def _handle_quit_command(self) -> FTPResponse:
        if self.should_return_error("QUIT"):
            return FTPResponse(500, "QUIT command failed")

        delay = self.get_command_delay("QUIT")
        if delay > 0:
            await asyncio.sleep(delay)

        if self.data_server:
            self.data_server.close()
        return FTPResponse(221, "Goodbye")

    async def handle_data_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        if self.store_mode:
            data = await reader.read()
            path = self.current_directory
            if not path.endswith('/'):
                path += '/'
            path += self.pending_store_filename
            self.vfs.store_file(path, data)
            print(f"Stored {len(data)} bytes to file {path}")
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
    def __init__(self, host='127.0.0.1', port=2121):
        self.host = host
        self.port = port
        self.running = False
        self.data_port = 2121
        self.current_directory = "/"
        self.command_handler = FTPCommandHandler(self.current_directory, self.host, self.data_port)

    async def start(self):
        self.running = True
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        print(f"FTP Mock Server running on {self.host}:{self.port}")

        async with server:
            await server.serve_forever()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        print(f"Client connected from {addr}")

        writer.write(FTPResponse(220, "Welcome to FTP Mock Server").encode())
        await writer.drain()

        while True:
            try:
                data = (await reader.read(1024)).decode().strip()
                if not data:
                    break

                print(f"> {data}")
                command = data.split(' ')[0]
                args = data[len(command):].strip()

                response = await self.command_handler.handle_command(command, args)
                writer.write(response.encode())
                print(f"< {response.code} {response.message}")
                await writer.drain()

                if response.code == 150:  # For LIST or STOR command
                    writer.write(FTPResponse(226, "Transfer complete").encode())
                    await writer.drain()

                if command.upper() == "QUIT":
                    break

            except Exception as e:
                print(f"Error handling client: {e}")
                break

        writer.close()
        await writer.wait_closed()

    def stop(self):
        self.running = False

def signal_handler(signum, frame):
    print("\nShutting down server...")
    server.stop()
    exit(0)

if __name__ == "__main__":
    server = FTPMockServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
