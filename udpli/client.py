#! RASP
import sys
import socket
import time
from picamera2 import Picamera2
import cv2
import struct

# Kullanıcıdan IP adresi ve port numarasını komut satırından al
UDP_IP = sys.argv[1]  # Alıcı bilgisayarın IP adresi
UDP_PORT = int(sys.argv[2])  # Alıcı bilgisayarın port numarası
# 61440
PACKET_SIZE = 60000  # UDP paket boyutu, 60 KB

# UDP soketi oluştur
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# PiCamera2'yi başlat ve yapılandır
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"format": "RGB888", "size": (640, 480)}))
picam2.start()
time.sleep(2)  # Kamera başlatma süresi için bekle

frame_counter = 0  # Çerçeve sayacını başlat

total_frame = 0
frame_time = time.time()
try:
    while True:
        # Kamera görüntüsünü yakala
        frame = picam2.capture_array()
        # Görüntüyü JPEG formatında sıkıştır
        _, buffer = cv2.imencode('.jpg', frame)
        buffer = buffer.tobytes()  # Veriyi baytlara dönüştür
        buffer_size = len(buffer)  # Verinin boyutunu al

        # Veriyi parçalara böl ve gönder
        for i in range(0, buffer_size, PACKET_SIZE):
            end = i + PACKET_SIZE
            if end > buffer_size:
                end = buffer_size
            packet = struct.pack('<L', frame_counter) + buffer[i:end]
            sock.sendto(packet, (UDP_IP, UDP_PORT))

        # Son paketle bir "son" işareti gönder
        sock.sendto(struct.pack('<L', frame_counter) + b'END', (UDP_IP, UDP_PORT))

        if frame_counter == 20000:
            frame_counter = 0
        frame_counter += 1  # Çerçeve sayacını artır
        total_frame += 1

        if time.time() - frame_time >= 0.1:
            print(f"FPS: {total_frame / (time.time() - frame_time)}")
            total_frame = 0
            frame_time = time.time()

except KeyboardInterrupt:
    print("Ctrl+C ile çıkıldı.")

finally:
    # Kamera ve soketi kapat
    print("Program sonlandırıldı.")
    picam2.stop()
    sock.close()
