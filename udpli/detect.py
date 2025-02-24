#! GIBI
import sys
import cv2
import socket
import numpy as np
import struct
from ultralytics import YOLO
import os
import time

model_name = "kullanilcak.pt"
model = YOLO("../models/" + model_name)

if len(sys.argv) != 2:
    print("Kod kullanımı python detect.py <port numarası>")
    exit()

# Kullanıcıdan IP adresi ve port numarasını komut satırından al
UDP_IP = "0.0.0.0"  # Alıcı bilgisayarın IP adresi
UDP_PORT = int(sys.argv[1])  # Alıcı bilgisayarın port numarası
BUFFER_SIZE = 65536  # UDP tampon boyutu, 64 KB

try:
    # UDP soketi oluştur ve belirtilen IP ve portta dinlemeye başla
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    buffer = b''  # Gelen veri parçalarını depolamak için tampon
    current_frame = -1  # Geçerli çerçeve numarasını takip etmek için sayaç

    start_time = time.time()

    with open("../gorev_dosyaları/ates_konum.txt", "w") as file:
        file.close()
    
    kaydet = True

    total_frame = 0
    
    frame_time = time.time()
    fps = 0
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)  # Maksimum UDP paket boyutu kadar veri al
        
        # Çerçeve numarasını çöz
        frame_number = struct.unpack('<L', data[:4])[0]
        packet_data = data[4:]

        if frame_number != current_frame:
            if buffer:
                # Görüntüyü verinin tamamı alındığında oluştur
                npdata = np.frombuffer(buffer, dtype=np.uint8)
                frame = cv2.imdecode(npdata, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    if time.time() - start_time > 0.1:
                        results = model(frame)
                        for r in results:
                            boxes = r.boxes
                            for box in boxes:
                                if box.conf[0] < 0.90:
                                    continue
                                # Sınırlayıcı kutu koordinatlarını al
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                                # Sınıf ve güven skorunu al
                                cls = int(box.cls[0].item())
                                conf = box.conf[0].item()

                                # Sınıf adını al
                                class_name = model.names[cls]

                                # Bilgileri ekrana yazdır
                                print(f"Sınıf: {class_name}, Güven: {conf:.2f}, Konum: ({x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}")

                                # Nesneyi çerçeve içine al ve etiketle
                                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                                cv2.putText(frame, f"{class_name} {conf:.2f}", (int(x1), int(y1 - 10)), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                                
                                # ates_konum.txt dosyası formatı:
                                # x1,y1,x2,y2\n
                                
                                if kaydet:
                                    with open("../gorev_dosyaları/ates_konum.txt", "a") as loc_file:
                                        loc_file.write(f"{x1},{y1},{x2},{y2}\n")
                                        kaydet = False

                        start_time = time.time()
                    
                    if time.time() - frame_time:
                        fps = total_frame / (time.time() - frame_time)
                        total_frame = 0
                        frame_time = time.time()

                    cv2.putText(frame, f"{fps:.1f}", (0, 25), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    cv2.imshow('YOLOv8 Canlı Tespit', frame)  # Görüntüyü göster
                
                buffer = b''  # Yeni görüntü için tamponu sıfırla

            current_frame = frame_number  # Geçerli çerçeve numarasını güncelle
            total_frame += 1

        if packet_data == b'END':
            # Son paket işareti, çerçevenin sonu
            continue

        buffer += packet_data  # Gelen veri parçasını tampona ekle

        # Çıkış için 'q' tuşuna basılması beklenir
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
except KeyboardInterrupt:
    print("Ctrl+C ile çıkıldı.")

finally:
    print("Program sonlandırıldı.")
    cv2.destroyAllWindows()  # Tüm OpenCV pencerelerini kapat
    sock.close()  # Soketi kapat
