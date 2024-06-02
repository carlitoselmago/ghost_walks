#include <SPI.h>
#include "DW1000Ranging.h"
#include <WiFi.h>
#include <WiFiUdp.h>


#define SPI_SCK 18
#define SPI_MISO 19
#define SPI_MOSI 23
#define DW_CS 4
 
// connection pins
const uint8_t PIN_RST = 27; // reset pin
const uint8_t PIN_IRQ = 34; // irq pin
const uint8_t PIN_SS = 4;   // spi select pin

const char* tagid = "tag1";
const char* ssid = "( o )( o )";
const char* password = "todojuntoyenminusculas";
const char* host = "192.168.1.139";  // Set this to your computer's IP address
const uint16_t port = 8888;


bool connecteddevices[10]={false,false,false,false,false,false,false,false,false,false};
float anchorsdistances[10]={0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0};

WiFiUDP udp;
char incomingPacket[255];  // Buffer for incoming packets


void setup()
{
    Serial.begin(115200);
    delay(1000);
    //init the configuration
    SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI);
    DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ); //Reset, CS, IRQ pin
    //define the sketch as anchor. It will be great to dynamically change the type of module
    DW1000Ranging.attachNewRange(newRange);
    DW1000Ranging.attachNewDevice(newDevice);
    DW1000Ranging.attachInactiveDevice(inactiveDevice);
    //Enable the filter to smooth the distance
    DW1000Ranging.useRangeFilter(true);
 
    //we start the module as a tag
    DW1000Ranging.startAsTag("01:00:22:EA:82:60:3B:9C", DW1000.MODE_LONGDATA_RANGE_LOWPOWER); // add to the first number 01, 02, 03

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
 
void loop()
{
    DW1000Ranging.loop();
}
 
void newRange()
{
    int id=getAnchorIntId(DW1000Ranging.getDistantDevice()->getShortAddress());
    float range=DW1000Ranging.getDistantDevice()->getRange();
    anchorsdistances[id-1]=range;
    Serial.print("from: ");
    Serial.print(id);
    //Serial.print(DW1000Ranging.getDistantDevice()->getShortAddress(), HEX);
    Serial.print("\t Range: ");
    Serial.print(DW1000Ranging.getDistantDevice()->getRange());
    Serial.println(" m");
    //Serial.print("\t RX power: ");
    //Serial.print(DW1000Ranging.getDistantDevice()->getRXPower());
    //Serial.println(" dBm");

    //get all active anchors distances and put them together in a single call
    String message ="{'tagid':'" + String(tagid) + "','anchors':[";
    // + String(x, 4) + ",'y':" + String(y, 4) + "}";
    for (int i=0; i<sizeof  anchorsdistances/sizeof  anchorsdistances[0]; i++)
				
				{
					int val =  anchorsdistances[i];
          if (val>0.0){
            message+=String(i+1)+":"+String(val)+",";
          }
              
				{
    message=removeLastChar(message); //remove last coma

    message+="]}";
    sendMessage(message);
    
}
 
void newDevice(DW1000Device *device) { 
    int id=getAnchorIntId(device->getShortAddress());
    //connecteddevices[id]=true;
    //Serial.print("ranging init; 1 device added ! -> ");
    //Serial.print(" short:");
    //Serial.println(device->getShortAddress(), HEX);
    Serial.print("NEW DEVICE CONNECTED: ");
    Serial.println(id);
}
 
void inactiveDevice(DW1000Device *device) {
    //Serial.print("delete inactive device: ");
    //Serial.println(device->getShortAddress(), HEX);
    int id=getAnchorIntId(device->getShortAddress());
    anchorsdistances[id-1]=0.0;
    //connecteddevices[id]=false;
    Serial.print("DEVICE DISCONNECTED: ");
    Serial.println(id);

}

String removeLastChar(String str) {
  int length = str.length();
  if (length > 0) {
    str.remove(length - 1); // Remove the last character
  }
  return str;
}


void sendMessage(String message) {
  udp.beginPacket(host, port);
  udp.write((const uint8_t*)message.c_str(), message.length());
  udp.endPacket();
}

int getAnchorIntId(uint16_t shortAddress) {
    // Convert the uint16_t to a string
    char shortAddressStr[5]; // Maximum 4 digits + null terminator
    snprintf(shortAddressStr, sizeof(shortAddressStr), "%04X", shortAddress);

    // Get the last two characters of the string
    char lastTwoChars[3]; // 2 chars + null terminator
    lastTwoChars[0] = shortAddressStr[2];
    lastTwoChars[1] = shortAddressStr[3];
    lastTwoChars[2] = '\0';

    // Convert the last two characters to an integer
    int value = atoi(lastTwoChars);

    // Subtract 80 from the value
    value -= 80;

    // Return the result
    return value;
}