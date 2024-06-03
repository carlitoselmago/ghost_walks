#include <SPI.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Arduino.h>
#include "driver/dac.h"
#include "DW1000Ranging.h"


#define SPI_SCK 18
#define SPI_MISO 19
#define SPI_MOSI 23
#define DW_CS 4

// connection pins
const uint8_t PIN_RST = 27; // reset pin
const uint8_t PIN_IRQ = 34; // irq pin
const uint8_t PIN_SS = 4;   // spi select pin

const char tagid[] = "tag1";
const char ssid[] = "( o )( o )";
const char password[] = "todojuntoyenminusculas";
const char host[] = "192.168.1.255";//"192.168.1.139";  // Set this to your computer's IP address
const uint16_t port = 8888;

bool connecteddevices[10] = {false, false, false, false, false, false, false, false, false, false};
float anchorsdistances[10] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

WiFiUDP udp;
char incomingPacket[255];  // Buffer for incoming packets

// Task handle for the sound task
TaskHandle_t soundTaskHandle;

volatile float delayamount=5000;

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
    dac_output_enable(DAC_CHANNEL_1); // Enable DAC channel (GPIO25 or GPIO26)

    // Create the sound task
  xTaskCreate(
    soundTask,          // Task function
    "Sound Task",       // Name of the task
    1000,               // Stack size (in words)
    NULL,               // Task input parameter
    1,                  // Priority of the task
    &soundTaskHandle    // Task handle
  );
}

void loop()
{
    DW1000Ranging.loop();
    recieveMessage();
}

void newRange()
{
    int id = getAnchorIntId(DW1000Ranging.getDistantDevice()->getShortAddress());
    float range = DW1000Ranging.getDistantDevice()->getRange();
    if (range>0.0){
      anchorsdistances[id - 1] = range;
      //Serial.print("from: ");
      //Serial.print(id);
      //Serial.print("\t Range: ");
      //Serial.print(DW1000Ranging.getDistantDevice()->getRange());
      //Serial.println(" m");

      // Get all active anchors distances and put them together in a single call
      char message[512];
      snprintf(message, sizeof(message), "{'tagid':'%s','anchors':{", tagid);

      char temp[50];
      for (int i = 0; i < 10; i++) {
          float val = anchorsdistances[i];
          if (val > 0.0) {
              snprintf(temp, sizeof(temp), "'%d':%.2f,", i + 1, val);
              strncat(message, temp, sizeof(message) - strlen(message) - 1);
          }
      }

      removeLastChar(message); // Remove last comma
      strncat(message, "}}", sizeof(message) - strlen(message) - 1);

      sendMessage(message);
    }
}

void newDevice(DW1000Device *device) {
    int id = getAnchorIntId(device->getShortAddress());
    Serial.print("NEW DEVICE CONNECTED: ");
    Serial.println(id);
}

void inactiveDevice(DW1000Device *device) {
    int id = getAnchorIntId(device->getShortAddress());
    anchorsdistances[id - 1] = 0.0;
    Serial.print("DEVICE DISCONNECTED: ");
    Serial.println(id);
}

void removeLastChar(char *str) {
    int length = strlen(str);
    if (length > 0) {
        str[length - 1] = '\0'; // Remove the last character
    }
}

void sendMessage(const char *message) {
    udp.beginPacket(host, port);
    udp.write((const uint8_t*)message, strlen(message));
    udp.endPacket();
}

void recieveMessage(){
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
      //Serial.printf("Received float: %f\n", receivedValue);
      //float receivedValue_inverted=(1.0-receivedValue);
      //delayamount=(1.0-receivedValue)*1000.0;
      delayamount= mapFloat(receivedValue, 0.0, 0.8, 3000.0, 20.0);  // Map from range 0-100 to range 0-255
      Serial.print("recievedvalue: ");
      Serial.print(receivedValue);
      Serial.printf(" - delay amount: %f\n", delayamount);
      /*
      //make the speaker sound
      // Maximize the DAC output
      for (int i = 0; i < 255; i++) {
        dac_output_voltage(DAC_CHANNEL_1, 255); // Use maximum voltage for the pulse
        delayMicroseconds(2); // Short burst
      }
      for (int i = 255; i >= 0; i--) {
        dac_output_voltage(DAC_CHANNEL_1, 0); // Drop to zero quickly
        delayMicroseconds(2); // Short burst
      }
      int delayamount=receivedValue*10000.0;
      Serial.print("delayamount: ");
      Serial.println(delayamount);
      delay(delayamount);
      //delay(random(100, 1000)); // Random delay between clicks
      //ledspeed=receivedValue*1000;
      */
    } else {
      Serial.println("Received packet is not a float.");
    }
  }
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

// Function to generate the tone
void soundTask(void * parameter) {
  while (true) {
    for (int i = 0; i < 255; i++) {
      dac_output_voltage(DAC_CHANNEL_1, 255); // Use maximum voltage for the pulse
      //digitalWrite(speakerPin, HIGH);
      delayMicroseconds(2);
    }
    for (int i = 255; i >= 0; i--) {
      dac_output_voltage(DAC_CHANNEL_1, 0); // Use maximum voltage for the pulse
      //digitalWrite(speakerPin, LOW);
      delayMicroseconds(2);
    }

   
    //Serial.print("delayamount: ");
    //Serial.println(delayamount);
    delay(delayamount);
  }
}


float mapFloat(float x, float in_min, float in_max, float out_min, float out_max) {
  float result = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
/*
  // Ensure the result is within the bounds
  if (result < out_min) {
    result = out_min;
  }
  if (result > out_max) {
    result = out_max;
  }
*/
  return result;
}