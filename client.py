# client.py
import socket
import struct
import cv2
import numpy as np
import threading
import json
import time

from pynput import mouse, keyboard

SERVER = '192.168.1.8'  # <-- ganti dengan IP host (server)
VIDEO_PORT = 5000
CONTROL_PORT = 5001

def recv_all(sock, n):
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def video_client():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER, VIDEO_PORT))
    print('Connected to video', SERVER, VIDEO_PORT)
    try:
        while True:
            hdr = recv_all(s, 8)
            if not hdr:
                break
            (length,) = struct.unpack('!Q', hdr)
            payload = recv_all(s, length)
            if not payload:
                break
            # decode JPEG
            arr = np.frombuffer(payload, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue
            cv2.imshow('Remote', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except Exception as e:
        print('Video client error', e)
    finally:
        s.close()
        cv2.destroyAllWindows()

# CONTROL (send local input events to server)
control_sock = None
control_lock = threading.Lock()

def send_control_event(evt):
    global control_sock
    if control_sock is None:
        return
    line = (json.dumps(evt) + '\n').encode('utf-8')
    try:
        with control_lock:
            control_sock.sendall(line)
    except Exception as e:
        print('Failed to send control', e)

# mouse handlers
def on_move(x, y):
    send_control_event({"type":"mouse_move","x":int(x),"y":int(y)})

def on_click(x, y, button, pressed):
    btn = 'left' if button == mouse.Button.left else 'right'
    action = 'press' if pressed else 'release'
    send_control_event({"type":"mouse_click","button":btn,"action":action})

def on_scroll(x, y, dx, dy):
    # optional: implement scroll
    send_control_event({"type":"scroll","dx":dx,"dy":dy})

def keyboard_on_press(key):
    k = None
    try:
        k = key.char
    except AttributeError:
        k = str(key).replace('Key.', '')
    send_control_event({"type":"key","key":k,"action":"press"})

def keyboard_on_release(key):
    try:
        k = key.char
    except AttributeError:
        k = str(key).replace('Key.', '')
    send_control_event({"type":"key","key":k,"action":"release"})
    if k == 'esc':
        # stop listener if needed
        return False

def control_client():
    global control_sock
    control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    control_sock.connect((SERVER, CONTROL_PORT))
    print('Connected to control', SERVER, CONTROL_PORT)
    # start local input listeners (note: be careful — this will capture all input on controller machine)
    ms = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    ks = keyboard.Listener(on_press=keyboard_on_press, on_release=keyboard_on_release)
    ms.start()
    ks.start()
    ms.join()
    ks.join()
    control_sock.close()

if __name__ == '__main__':
    # start control thread first
    t = threading.Thread(target=control_client, daemon=True)
    t.start()
    time.sleep(0.5)
    video_client()
