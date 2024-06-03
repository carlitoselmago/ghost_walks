#include <WiFi.h>
#include <WiFiUdp.h>

const char* tagid = "tag1";
const char* ssid = "( o )( o )";
const char* password = "todojuntoyenminusculas";
const char* host = "192.168.1.139";  // Set this to your computer's IP address
const uint16_t port = 8888;

WiFiUDP udp;
char incomingPacket[255];  // Buffer for incoming packets
int LED_BUILTIN = 2;
int ledspeed=100;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }

  Serial.println("Connected to WiFi");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());
  udp.begin(port);  // Start UDP
}

void loop() {
  //send
  float x = random(0, 100) / 100.0;  // Generate random float between 0.0 and 1.0
  float y = random(0, 100) / 100.0;  // Generate random float between 0.0 and 1.0

  String message ="{'tagid':'" + String(tagid) + "','x':" + String(x, 4) + ",'y':" + String(y, 4) + "}";
  sendMessage(message);
  delay(10); 

  //recieve
  int packetSize = udp.parsePacket();
  if (packetSize) {
    // Receive incoming UDP packets
    int len = udp.read(incomingPacket, 255);
    if (len > 0) {
      incomingPacket[len] = 0;
    }
    //Serial.printf("Received packet of size %d from %s:%d\n", packetSize, udp.remoteIP().toString().c_str(), udp.remotePort());
    //Serial.printf("Packet contents: %s\n", incomingPacket);

    // Convert incoming packet to float if the expected size is received
    if (packetSize == sizeof(float)) {
      float receivedValue;
      memcpy(&receivedValue, incomingPacket, sizeof(receivedValue));
      Serial.printf("Received float: %f\n", receivedValue);
      //ledspeed=receivedValue*1000;
    } else {
      Serial.println("Received packet is not a float.");
    }
  }
  //digitalWrite(LED_BUILTIN, HIGH);  // turn the LED on (HIGH is the voltage level)
  //delay((int)ledspeed);                      // wait for a second
  //digitalWrite(LED_BUILTIN, LOW);   // turn the LED off by making the voltage LOW
  //delay((int)ledspeed); 
}

void sendMessage(String message) {
  udp.beginPacket(host, port);
  udp.write((const uint8_t*)message.c_str(), message.length());
  udp.endPacket();
  //Serial.println("Message sent: " + message);  // Debug print
}
