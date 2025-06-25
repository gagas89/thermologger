# tkinter is not available in this environment, so we cannot execute this code here.
# However, you can run this script on your local Python installation that supports tkinter (such as on Windows/macOS/Linux with GUI).

# Save this code as esp32_gui.py and run it using: python esp32_gui.py

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import serial
import serial.tools.list_ports
import threading
import time
import queue
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tksheet import Sheet
import csv
from datetime import datetime
import tkinter.messagebox as messagebox

# ============ Serial Communication Manager ============
class SerialManager:
    def __init__(self):
        self.ser = None
        self.port = None
        self.baudrate = 9600
        self.receive_thread = None
        self.running = False
        self.data_queue = queue.Queue()
        self.latest_data = None

    def list_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.running = True
            self.receive_thread = threading.Thread(target=self.read_data)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            return True
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return False

    def disconnect(self):
        self.running = False
        if self.ser:
            self.ser.close()
            self.ser = None

    def read_data(self):
        while self.running:
            if self.ser and self.ser.in_waiting:
                try:
                    line = self.ser.readline().decode().strip()
                    parts = line.split(',')
                    if len(parts) == 4:
                        temps = list(map(float, parts))
                        self.latest_data = (time.time(), temps)
                        self.data_queue.put(self.latest_data)
                except:
                    pass

    def get_latest_data(self):
        return self.latest_data

    def get_data_from_queue(self):
        data = []
        while not self.data_queue.empty():
            data.append(self.data_queue.get())
        return data

# ============ App Base ============
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ESP32 Temperature Logger")
        self.geometry("1100x800")

        self.serial_manager = SerialManager()

        serial_frame = ttk.LabelFrame(self, text="Serial Connection")
        serial_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(serial_frame, text="Port:").pack(side='left')
        self.port_cb = ttk.Combobox(serial_frame, values=self.serial_manager.list_ports(), width=10)
        if self.serial_manager.list_ports():
            self.port_cb.set(self.serial_manager.list_ports()[0])

        self.port_cb.pack(side='left', padx=5)

        ttk.Button(serial_frame, text="Refresh", command=self.refresh_ports).pack(side='left', padx=5)

        ttk.Label(serial_frame, text="Baudrate:").pack(side='left')
        self.baud_cb = ttk.Combobox(serial_frame, values=[9600, 19200, 38400, 115200], width=10)
        self.baud_cb.set(115200)
        self.baud_cb.pack(side='left', padx=5)

        self.connect_btn = ttk.Button(serial_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side='left', padx=5)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.realtime_page = RealTimePage(self)
        self.datarecorder_page = DataRecorderPage(self)

        self.notebook.add(self.realtime_page, text="Real Time")
        self.notebook.add(self.datarecorder_page, text="Data Recorder")

        self.update_loop()
        self.update_recording_loop()

    def refresh_ports(self):
        self.port_cb['values'] = self.serial_manager.list_ports()

    def toggle_connection(self):
        if self.serial_manager.ser:
            self.serial_manager.disconnect()
            self.connect_btn.config(text="Connect")
        else:
            port = self.port_cb.get()
            baud = int(self.baud_cb.get())
            if self.serial_manager.connect(port, baud):
                self.connect_btn.config(text="Disconnect")

    def update_loop(self):
        self.realtime_page.update_display()
        self.datarecorder_page.update_recording()
        self.after(1000, self.update_loop)

    def update_recording_loop(self):
        self.datarecorder_page.update_recording()
        self.after(200, self.update_recording_loop)


# ============ Real Time Page ============
class RealTimePage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent.notebook)
        self.parent = parent
        self.temp_labels = []

        for i in range(4):
            frame = ttk.Frame(self)
            frame.pack(pady=5)
            ttk.Label(frame, text=f"Sensor {i+1}: ").pack(side='left')
            var = tk.StringVar(value="--.- °C")
            label = ttk.Label(frame, textvariable=var, font=('Arial', 16))
            label.pack(side='left')
            self.temp_labels.append(var)

        self.fig, self.ax = plt.subplots(figsize=(6, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(pady=10, fill='both', expand=True)
        self.plot_data = [[] for _ in range(4)]

    def update_display(self):
        result = self.parent.serial_manager.get_latest_data()
        if result:
            t_now, temps = result
            for i in range(4):
                self.temp_labels[i].set(f"{temps[i]:.2f} °C")
                self.plot_data[i].append((t_now, temps[i]))

            self.ax.clear()
            for i, data in enumerate(self.plot_data):
                if data:
                    x, y = zip(*data)
                    x0 = x[0]
                    self.ax.plot([t - x0 for t in x], y, label=f"Sensor {i+1}")
            self.ax.set_xlabel("Time (s)")
            self.ax.set_ylabel("Temperature (°C)")
            self.ax.legend()
            self.canvas.draw()

# ============ Data Recorder Page ============
class DataRecorderPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent.notebook)
        self.parent = parent
        self.recording = [False] * 4
        self.data = [[] for _ in range(4)]
        self.last_sample_time = [0] * 4

        param_frame = ttk.Frame(self)
        param_frame.pack(pady=10)

        ttk.Label(param_frame, text="Record Duration (min):").pack(side='left')
        self.duration_var = tk.IntVar(value=1)
        ttk.Entry(param_frame, textvariable=self.duration_var, width=5).pack(side='left')

        ttk.Label(param_frame, text="Sample Period (s):").pack(side='left', padx=5)
        self.period_var = tk.IntVar(value=10)
        ttk.Entry(param_frame, textvariable=self.period_var, width=5).pack(side='left')

        control_frame = ttk.Frame(self)
        control_frame.pack()

        all_btn_frame = ttk.Frame(control_frame)
        all_btn_frame.grid(row=0, column=0, columnspan=4, pady=5)
        ttk.Button(all_btn_frame, text="Start All", command=self.start_all).pack(side='left', padx=10)
        ttk.Button(all_btn_frame, text="Stop All", command=self.stop_all).pack(side='left', padx=10)

        self.buttons = []
        self.status_labels = []
        self.trial_name = []
        for i in range(4):
            col = ttk.Frame(control_frame)
            col.grid(row=1, column=i, padx=10)
            ttk.Label(col, text=f"Sensor {i+1}").pack()
            status = ttk.Label(col, text="Idle", foreground="gray")
            status.pack()
            start_btn = ttk.Button(col, text="Start", command=lambda i=i: self.start_record(i))
            stop_btn = ttk.Button(col, text="Stop", command=lambda i=i: self.stop_record(i))
            start_btn.pack()
            stop_btn.pack() 
            strvar = tk.StringVar()
            self.trial_name.append(strvar)
            ttk.Label(col, text=f"Title {i+1}").pack()
            ttk.Entry(col, textvariable=strvar, width=20).pack()
            self.buttons.append((start_btn, stop_btn))
            self.status_labels.append(status)

        table_frame = ttk.Frame(self)
        table_frame.pack(pady=10, fill='both', expand=True)

        self.tables = []
        for i in range(4):
            sub_frame = ttk.Frame(table_frame)
            sub_frame.grid(row=0, column=i, padx=10, sticky='n')
            ttk.Label(sub_frame, text=f"Sensor {i+1} Data").pack()
            sheet = Sheet(sub_frame, 
                          headers=["Time (s)", "Temp (°C)", "Timestamp"], 
                          column_width=140
                          )
            sheet.pack(fill='both', expand=True)
            self.tables.append(sheet)
            
        ttk.Button(self, text="Export to CSV", command=self.export_to_csv).pack(pady=5)

        self.fig, self.ax = plt.subplots(figsize=(6, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(pady=10, fill='both', expand=True)

    def start_record(self, sensor_id):
        self.recording[sensor_id] = True
        self.data[sensor_id] = []
        self.last_sample_time[sensor_id] = -self.period_var.get()
        self.status_labels[sensor_id].config(text="Recording", foreground="green")
        self.refresh_table()
        self.refresh_graph()

    def stop_record(self, sensor_id):
        self.recording[sensor_id] = False
        self.status_labels[sensor_id].config(text="Idle", foreground="gray")

    def start_all(self):
        for i in range(4):
            self.start_record(i)

    def stop_all(self):
        for i in range(4):
            self.stop_record(i)

    def update_recording(self):
        result = self.parent.serial_manager.get_latest_data()
        if not result:
            return
        t_now, temps = result

        for i in range(4):
            if self.recording[i]:
                if (t_now - self.last_sample_time[i]) >= self.period_var.get():
                    elapsed = t_now - self.data[i][0][0] if self.data[i] else 0
                    self.data[i].append((t_now, temps[i], datetime.fromtimestamp(t_now).strftime("%Y-%m-%d %H:%M:%S")))
                    self.last_sample_time[i] = t_now
                    self.refresh_table()
                    self.refresh_graph()
                if self.data[i] and (t_now - self.data[i][0][0]) >= self.duration_var.get() * 60:
                    self.recording[i] = False
                    self.status_labels[i].config(text="Idle", foreground="gray")

    def refresh_table(self):
        for i in range(4):
            if self.data[i]:
                t0 = self.data[i][0][0]
                rows = [[f"{t - t0:.1f}", f"{v:.2f}", ts] for t, v, ts in self.data[i]]
                self.tables[i].set_sheet_data(rows)

    def refresh_graph(self):
        self.ax.clear()
        for i, d in enumerate(self.data):
            if d:
                t0 = d[0][0]
                x = [t - t0 for t, _, _ in d]
                y = [v for _, v, _ in d]
                self.ax.plot(x, y, label=f"Sensor {i+1}")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Temperature (°C)")
        self.ax.legend()
        self.canvas.draw()

    def export_to_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[["CSV Files", "*.csv"]])
        if not file_path:
            return
        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Title","Sensor", "Time (s)", "Temp (°C)", "Timestamp"])
                for sensor_id, d in enumerate(self.data):
                    if d:
                        t0 = d[0][0]
                        for t, temp, ts in d:
                            writer.writerow([self.trial_name[sensor_id].get(), f"Sensor {sensor_id+1}", f"{t - t0:.1f}", f"{temp:.2f}", ts])
            messagebox.showinfo("Export Successful", f"Data exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

if __name__ == '__main__':
    app = App()
    app.mainloop()
