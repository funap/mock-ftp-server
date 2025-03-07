# FTP Mock Server

A configurable mock FTP server for testing purposes written in Python. This server simulates basic FTP functionality with a virtual file system and customizable response behaviors.

## Features

- Virtual file system with predefined directories and files
- Support for basic FTP commands (USER, PASS, PWD, TYPE, PASV, LIST, CWD, STOR, QUIT)
- GUI control panel for command response configuration
- Configurable error responses and delays per command
- Real-time logging of FTP commands and responses
- Support for passive mode file transfers
- File upload capability (STOR command)

## Installation

```bash
git clone https://github.com/funap/mock-ftp-server.git
cd ftp-mock-server
```

## Usage

Start the server (default port 8021):
```bash
python ftpd.py
```

With custom port:
```bash
python ftpd.py --port 2121
```

## Default Virtual File System Structure

```
/
├── README.txt
├── data.bin
├── docs/
│   ├── manual.pdf
│   ├── specs.doc
│   └── specs/
│       └── api.md
└── images/
    ├── photo.jpg
    ├── icon.png
    └── thumbnails/
        └── thumb1.jpg
```

## GUI Control Panel

The server includes a GUI control panel that allows you to:
- Toggle error responses for specific FTP commands
- Set response delays (0-10 seconds) for each command
- Monitor server activity in real-time

## Supported FTP Commands

- USER - User authentication
- PASS - Password authentication
- PWD - Print working directory
- TYPE - Set transfer type
- PASV - Enter passive mode
- LIST - List directory contents
- CWD - Change working directory
- STOR - Upload file
- QUIT - Close connection

## Testing

Connect to the server using any FTP client:
```bash
ftp localhost 8021
```

## License

This project is licensed under the MIT License

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request
