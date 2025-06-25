import tkinter as tk
from tkinter import ttk
import serial
import threading
import time
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Serial port config
SERIAL_PORT = 'COM8'  # Replace with your port
BAUD_RATE = 115200

# Global data store
sensor_data = []

class ESP32MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 DS18B20 Monitor")
        
        self.serial_conn = serial.Serial()
        self.serial_conn.port = SERIAL_PORT
        self.serial_conn.baudrate = BAUD_RATE
        self.serial_conn.timeout = 1

        self.data_frame = pd.DataFrame(columns=['Timestamp', 'Sensor1', 'Sensor2', 'Sensor3', 'Sensor4'])

        self.create_widgets()
        self.running = False

    def create_widgets(self):
        self.start_btn = tk.Button(self.root, text="Start", command=self.start_reading)
        self.start_btn.grid(row=0, column=0)

        self.stop_btn = tk.Button(self.root, text="Stop", command=self.stop_reading)
        self.stop_btn.grid(row=0, column=1)

        # Data Grid
        self.tree = ttk.Treeview(self.root, columns=("Sensor1", "Sensor2", "Sensor3", "Sensor4"), show='headings')
        for i in range(1, 5):
            self.tree.heading(f"Sensor{i}", text=f"Sensor {i}")
        self.tree.grid(row=1, column=0, columnspan=4)

        # Graph area
        self.figure = plt.Figure(figsize=(6, 3), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.line_plot = FigureCanvasTkAgg(self.figure, self.root)
        self.line_plot.get_tk_widget().grid(row=2, column=0, columnspan=4)

    def start_reading(self):
        if not self.running:
            try:
                self.serial_conn.open()
                self.running = True
                self.thread = threading.Thread(target=self.read_serial)
                self.thread.start()
            except Exception as e:
                print(f"Error opening serial: {e}")

    def stop_reading(self):
        self.running = False
        if self.serial_conn.is_open:
            self.serial_conn.close()

    def read_serial(self):
        while self.running:
            try:
                line = self.serial_conn.readline().decode().strip()
                if line:
                    print(f"Received: {line}")
                    parts = line.split(",")  # Expected: 4 comma-separated values
                    if len(parts) == 4:
                        timestamp = time.strftime("%H:%M:%S")
                        float_values = [float(x) for x in parts]
                        self.data_frame.loc[len(self.data_frame)] = [timestamp] + float_values

                        self.tree.insert('', 'end', values=float_values[-4:])

                        # Keep only the last 20 entries for the graph
                        if len(self.data_frame) > 20:
                            self.data_frame = self.data_frame.tail(20).reset_index(drop=True)

                        self.update_graph()
            except Exception as e:
                print(f"Serial read error: {e}")

    def update_graph(self):
        self.ax.clear()
        for i in range(1, 5):
            self.ax.plot(self.data_frame['Timestamp'], self.data_frame[f'Sensor{i}'], label=f'Sensor {i}')
        self.ax.legend(loc='upper left')
        self.ax.set_title("Temperature Readings")
        self.ax.set_ylabel("°C")
        self.ax.set_xlabel("Time")
        self.figure.autofmt_xdate()
        self.line_plot.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = ESP32MonitorApp(root)
    root.mainloop()
