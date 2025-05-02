# 📡 WiFi Network Scanner & Deauther

A Python-based graphical tool for wireless network scanning and testing with a Kali Linux-inspired interface. 🖥️

## 👥 Authors
- [Maksio2019](https://github.com/Maksio2019) 🧑‍💻
- Claude AI (Assistant) 🤖

## 🚀 Features
- 🎨 Clean and intuitive graphical interface
- 📡 Support for both 2.4GHz and 5GHz band scanning
- ⏱️ Configurable scan duration
- 📊 Network sorting by signal strength
- ✅ Multiple network selection capability
- 🔄 Real-time deauthentication status
- 🛠️ Interface monitor mode management

## 📋 Requirements
- 🐧 Linux-based system
- 🐍 Python 3.x
- 🔑 Root privileges
- 📡 Wireless adapter supporting monitor mode

### 📦 Required Python packages:
```bash
pip install scapy tk
```

### 🛠️ System tools:
```bash
sudo apt install aircrack-ng
```

## ⚠️ Important Notices

### 🚨 Legal Warning
This tool is for **educational and authorized testing purposes only**. Usage on networks without explicit permission is illegal!

### 💻 Hardware Requirements
- 📡 Your wireless adapter MUST support monitor mode operation
- ⚡ Not all cards support deauthentication on both bands

### 📡 Dual-Band Support
- ✨ Full scanning support for both 2.4GHz and 5GHz bands
- ⚡ Deauthentication capabilities vary by hardware
- ℹ️ Some cards may only support deauthentication on specific bands
- 🔍 Testing recommended before deployment

## 🚀 Usage
1. Clone the repository
2. Run with sudo privileges:
```bash
sudo python3 wifi_deauther.py
```
3. 🎯 Select your wireless interface
4. 🔄 Interface will automatically be set to monitor mode
5. 🖱️ Use the GUI to scan and manage networks

## ⚠️ Disclaimer
This tool is provided for educational purposes only. Users are responsible for ensuring compliance with local laws and regulations regarding network security testing.

## 🤝 Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.
