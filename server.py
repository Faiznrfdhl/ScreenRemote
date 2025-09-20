import socket
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab, Image, ImageTk
import io
import struct

# =====================
# SERVER (yang dishare)
# =====================
class ScreenServer:
    def __init__(self, host="0.0.0.0", port=9999):
        self.host = host
        self.port = port
        self.running = False

    def start(self):
        self.running = True
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(1)
        print(f"[SERVER] Listening on {self.host}:{self.port}")

        conn, addr = server.accept()
        print(f"[SERVER] Client connected: {addr}")

        try:
            while self.running:
                img = ImageGrab.grab()
                img = img.resize((800, 600))  # supaya gak terlalu berat
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG")
                data = buffer.getvalue()

                # kirim panjang data dulu
                conn.sendall(struct.pack(">I", len(data)) + data)
        except Exception as e:
            print(f"[SERVER] Error: {e}")
        finally:
            conn.close()
            server.close()

    def stop(self):
        self.running = False
        print("[SERVER] Stopped.")


# =====================
# CLIENT (yang nonton)
# =====================
class ScreenClient:
    def __init__(self, host="127.0.0.1", port=9999):
        self.host = host
        self.port = port
        self.running = False

    def start(self):
        self.running = True
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((self.host, self.port))

        # GUI Tkinter
        self.root = tk.Tk()
        self.root.title("Remote Desktop Client")

        self.label = tk.Label(self.root)
        self.label.pack()

        btn_stop = tk.Button(self.root, text="Stop", command=self.stop)
        btn_stop.pack()

        def update_frame():
            try:
                while self.running:
                    # ambil panjang data
                    raw_len = self.recvall(client, 4)
                    if not raw_len:
                        break
                    length = struct.unpack(">I", raw_len)[0]

                    # ambil gambar
                    data = self.recvall(client, length)
                    img = Image.open(io.BytesIO(data))
                    img_tk = ImageTk.PhotoImage(img)

                    self.label.config(image=img_tk)
                    self.label.image = img_tk
                    self.root.update_idletasks()
                    self.root.update()
            except Exception as e:
                print(f"[CLIENT] Error: {e}")
                messagebox.showerror("Error", str(e))
            finally:
                client.close()

        threading.Thread(target=update_frame, daemon=True).start()
        self.root.mainloop()

    def recvall(self, sock, size):
        data = b""
        while len(data) < size:
            packet = sock.recv(size - len(data))
            if not packet:
                return None
            data += packet
        return data

    def stop(self):
        self.running = False
        self.root.quit()
        print("[CLIENT] Stopped.")


# =====================
# JALANIN
# =====================
if __name__ == "__main__":
    mode = input("Pilih mode (server/client): ").strip().lower()
    if mode == "server":
        server = ScreenServer()
        server.start()
    elif mode == "client":
        host = input("Masukkan IP server (default 127.0.0.1): ") or "127.0.0.1"
        client = ScreenClient(host=host)
        client.start()
    else:
        print("Mode tidak dikenal!")
