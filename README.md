# KSU4IRTC UMN Batch 8 Group A - Implementasi Sorting Tomat

## Pengantar

Proyek ini dibuat untuk belajar mengenai communication protocol dari Raspberry Pi dan Server menggunakan MQTT

Raspberry Pi terhubung dengan Arduino (USB, UART) menerima serialized data IR (infrared) sensor lalu menjalankan model klasifikasi tomat dengan mengambil input 1 frame video dari kamera, lalu dipraproses (resize 320x320 default dan rescale 1./255.0), kemudian diprediksi.

Raspberry Pi mengirim data hasil prediksi menggunakan MQTT (publish message ke topic tertentu di broker)

Server melihat ada data baru di broker MQTT (subscribe ke topic tertentu di broker), lalu request API untuk insert data, menggunakan HTTP. Terkait format data dan sebagainya dapat dilakukan di server juga.
