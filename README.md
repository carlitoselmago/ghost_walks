# Ghost walks UWB
Code for Server (Linux), tag and anchor (ESP32)

UDP Com port: 8888

## Server
run 
```server.py
```
to store and send back data to the tags
run 
```python script.py -gui
```
to open a pygame window and track tags live

on Fedora run this before running server with gui
```
export LD_PRELOAD=/usr/lib64/libstdc++.so.6
```
