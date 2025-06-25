import tkinter as tk
from tkinter import scrolledtext
import serial
import threading

# === CONFIGURATION === Aseloleeeeee
SERIAL_PORT = 'COM8'      # Change to your port
BAUD_RATE = 115200

# === SERIAL HANDLER ===
class SerialHandler:
    def __init__(self, port, baud):
        self.serial = serial.Serial(port, baud, timeout=0.1)
        self.lock = threading.Lock()

    def read(self):
        with self.lock:
            return self.serial.read(self.serial.in_waiting or 1).decode(errors='ignore')

    def write(self, data):
        with self.lock:
            self.serial.write(data.encode())

    def close(self):
        if self.serial and self.serial.is_open:
            self.serial.close()

# === GUI ===
class SerialGUI:
    def __init__(self, master, serial_handler):
        self.master = master
        self.serial_handler = serial_handler

        master.title("Live Serial Monitor")

        self.text_box = scrolledtext.ScrolledText(master, wrap=tk.WORD, font=("Courier", 12))
        self.text_box.pack(expand=True, fill='both')
        self.text_box.configure(state='disabled')

        master.bind("<Key>", self.key_pressed)
        self.read_serial()

    def key_pressed(self, event):
        char = event.char
        if char:
            self.serial_handler.write(char)

    def read_serial(self):
        incoming = self.serial_handler.read()
        if incoming:
            self.text_box.configure(state='normal')
            self.text_box.insert(tk.END, incoming)
            self.text_box.see(tk.END)
            self.text_box.configure(state='disabled')
        self.master.after(100, self.read_serial)

    def on_close(self):
        self.serial_handler.close()
        self.master.destroy()

# === MAIN ===
if __name__ == "__main__":
    root = tk.Tk()
    try:
        serial_handler = SerialHandler(SERIAL_PORT, BAUD_RATE)
        app = SerialGUI(root, serial_handler)
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        root.mainloop()
    except serial.SerialException as e:
        print(f"Error: {e}")
