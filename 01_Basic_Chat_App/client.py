import socket
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox

class ChatClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tkinter Chat Client")
        self.minsize(560, 420)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Networking
        self.sock: socket.socket | None = None
        self.recv_thread: threading.Thread | None = None
        self.inbox = queue.Queue()
        self.connected = False

        self._build_ui()
        self.after(50, self._drain_inbox)

    def _build_ui(self):
        # Top connection frame
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Host:").pack(side=tk.LEFT)
        self.host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(top, textvariable=self.host_var, width=18).pack(side=tk.LEFT, padx=(4, 10))

        ttk.Label(top, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="12345")
        ttk.Entry(top, textvariable=self.port_var, width=8).pack(side=tk.LEFT, padx=(4, 10))

        ttk.Label(top, text="Name:").pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value="Guest")
        ttk.Entry(top, textvariable=self.name_var, width=14).pack(side=tk.LEFT, padx=(4, 10))

        self.connect_btn = ttk.Button(top, text="Connect", command=self.connect)
        self.connect_btn.pack(side=tk.LEFT)
        self.disconnect_btn = ttk.Button(top, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=(6,0))

        # Chat display
        mid = ttk.Frame(self, padding=(8, 0))
        mid.pack(fill=tk.BOTH, expand=True)

        self.chat = tk.Text(mid, height=18, wrap=tk.WORD, state=tk.DISABLED)
        self.chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        yscroll = ttk.Scrollbar(mid, command=self.chat.yview)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat["yscrollcommand"] = yscroll.set

        # Bottom entry/send
        bottom = ttk.Frame(self, padding=8)
        bottom.pack(fill=tk.X)

        self.msg_var = tk.StringVar()
        self.entry = ttk.Entry(bottom, textvariable=self.msg_var)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda e: self.send_message())

        self.send_btn = ttk.Button(bottom, text="Send", command=self.send_message, state=tk.DISABLED)
        self.send_btn.pack(side=tk.LEFT, padx=(8,0))

        # Status bar
        self.status_var = tk.StringVar(value="Disconnected")
        status = ttk.Label(self, textvariable=self.status_var, anchor=tk.W)
        status.pack(fill=tk.X, padx=8, pady=(0,6))

    # ---------------- Networking -----------------
    def connect(self):
        if self.connected:
            return
        host = self.host_var.get().strip()
        name = self.name_var.get().strip() or "Guest"
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be an integer.")
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((host, port))
            self.sock.settimeout(None)
            # Introduce ourselves
            self._send_line(f"/join {name}")
            self.connected = True
            self._set_connected_ui(True)
            self.status_var.set(f"Connected to {host}:{port} as {name}")
            # Start receiver thread
            self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self.recv_thread.start()
        except Exception as e:
            self.connected = False
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None
            messagebox.showerror("Connection Error", str(e))

    def disconnect(self):
        if not self.connected:
            return
        try:
            self._send_line("/quit")
        except Exception:
            pass
        try:
            if self.sock:
                self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.connected = False
        self._set_connected_ui(False)
        self.status_var.set("Disconnected")

    def _send_line(self, text: str):
        if self.sock:
            self.sock.sendall((text + "\n").encode("utf-8", errors="ignore"))

    def send_message(self):
        if not self.connected:
            return
        text = self.msg_var.get().strip()
        if not text:
            return
        if text == "/clear":
            self._clear_chat()
            self.msg_var.set("")
            return
        try:
            self._send_line(text)
        except Exception as e:
            messagebox.showerror("Send Failed", str(e))
            self.disconnect()
            return
        self.msg_var.set("")

    def _recv_loop(self):
        assert self.sock is not None
        file = self.sock.makefile("r", encoding="utf-8", newline="\n")
        try:
            for line in file:
                self.inbox.put(line.rstrip("\n"))
        except Exception:
            pass
        finally:
            self.inbox.put("[System] Connection closed.")

    def _drain_inbox(self):
        try:
            while True:
                line = self.inbox.get_nowait()
                self._append_chat(line)
        except queue.Empty:
            pass
        self.after(50, self._drain_inbox)

    # ---------------- UI Helpers -----------------
    def _append_chat(self, text: str):
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, text + "\n")
        self.chat.see(tk.END)
        self.chat.config(state=tk.DISABLED)

    def _clear_chat(self):
        self.chat.config(state=tk.NORMAL)
        self.chat.delete("1.0", tk.END)
        self.chat.config(state=tk.DISABLED)

    def _set_connected_ui(self, connected: bool):
        self.connect_btn.config(state=tk.DISABLED if connected else tk.NORMAL)
        self.disconnect_btn.config(state=tk.NORMAL if connected else tk.DISABLED)
        self.send_btn.config(state=tk.NORMAL if connected else tk.DISABLED)
        self.entry.config(state=tk.NORMAL if connected else tk.DISABLED)

    def on_close(self):
        self.disconnect()
        self.destroy()


if __name__ == "__main__":
    # Use themed widgets if available
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Fix blurry fonts on Windows
    except Exception:
        pass

    app = ChatClient()
    app.mainloop()