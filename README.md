# Ghost walks UWB
Code for Server (Linux), tag and anchor (ESP32)

UDP Com port: 8888

## Server
to store and send back data to the tags run 
```
server.py
```

to open a pygame window and track tags live run 
```
python script.py -gui
```


on Fedora run this before running server with gui
```
export LD_PRELOAD=/usr/lib64/libstdc++.so.6
```
