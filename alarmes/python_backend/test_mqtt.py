import paho.mqtt.client as mqtt

cfg = {
    "host": "m1.tuyaeu.com",
    "port": 8883,
    "client_id": "tuyapy_c8uhx3vs89grhea8mg7p",
    "username": "02e1a10f99ca32f8d9722a7a08f6a87c",
    "password": "02e1a10f99ca32f8d9722a7a08f6a87c",
}
print("Connecting with config", cfg)

client = mqtt.Client(client_id=cfg['client_id'])
client.username_pw_set(cfg['username'], cfg['password'])
import ssl
client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

def on_connect(c, userdata, flags, rc):
    print("on_connect rc", rc)

client.on_connect = on_connect

client.connect(cfg['host'], cfg['port'], keepalive=60)
client.loop_start()
import time
for i in range(5):
    time.sleep(1)

client.loop_stop()
client.disconnect()
