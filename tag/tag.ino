#include <SPI.h>
#include <WiFi.h>
//#include <WiFiUdp.h>
#include <ArduinoOSCWiFi.h>
#include "DW1000Ranging.h"
#include "DW1000.h"
#include "driver/dac.h"
#include <string.h>

#define SPI_SCK 18
#define SPI_MISO 19
#define SPI_MOSI 23
#define DW_CS 4

// connection pins
const uint8_t PIN_RST = 27; // reset pin
const uint8_t PIN_IRQ = 34; // irq pin
const uint8_t PIN_SS = 4;   // spi select pin

const char *tagid = "/tag2";
const char ssid[] = "MANGO";
const char password[] = "remotamente";
const char host[] = "192.168.2.255";//"192.168.10.255";//"192.168.1.139";  // Set this to your computer's IP address
const uint16_t port = 8888;


float ranges[10] ={0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0};

float presence=0.0;
float soundpresence=0.0;
float soundpresencestep=0.001;

int runtimesteps=0;

// Create a char array with enough space for the concatenated result
char tagid_listen[50]; // Adjust size as needed


// TAG antenna delay defaults to 16384
// leftmost two bytes below will become the "short address"
char tag_addr[] = "7D:00:22:EA:82:60:3B:9C";


WiFiUDP udp;

// Task handle for the sound task
TaskHandle_t OSCTaskHandle;

// Task handle for the sound task
TaskHandle_t soundTaskHandle;

void setup()
{
  Serial.begin(115200);
  delay(1000);

  // Copy the initial string into the char array
  strcpy(tagid_listen, tagid);

  // Concatenate the additional characters
  strcat(tagid_listen, "_listen");

  //Serial.println(tagid_listen);
  //initialize configuration
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI);
  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ); //Reset, CS, IRQ pin

  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.attachNewDevice(newDevice);
  DW1000Ranging.attachInactiveDevice(inactiveDevice);

  // start as tag, do not assign random short address

  DW1000Ranging.startAsTag(tag_addr, DW1000.MODE_LONGDATA_RANGE_LOWPOWER, false);

  WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.println("Connecting to WiFi...");
    }

    Serial.println("Connected to WiFi");
    Serial.print("ESP32 IP Address: ");
    Serial.println(WiFi.localIP());
    udp.begin(port);  // Start UDP

  
  // Create the udp task
  xTaskCreatePinnedToCore(
    OSCTask,          // Task function
    "UDP Task",       // Name of the task
    2000,               // Stack size (in words)
    NULL,               // Task input parameter
    3,                  // Priority of the task
    &OSCTaskHandle,  // Task handle
    1                 // core to run the task
  );


     // Create the sound task
  xTaskCreatePinnedToCore(
  //xTaskCreate(
    soundTask,          // Task function
    "Sound Task",       // Name of the task
    1000,               // Stack size (in words)
    NULL,               // Task input parameter
    4,                  // Priority of the task
    &soundTaskHandle ,   // Task handle
    1                 // core to run the task
  );
  
  // Set up OSC listener for the specific address
  OscWiFi.subscribe(port, tagid_listen,
    [&](const OscMessage& msg) {
     
      // Check if the message contains at least one argument
      if (msg.size() > 0) {
        // Retrieve and print the first argument as a float
        float value = msg.arg<float>(0);
        //Serial.print("Presence value: ");
        //Serial.println(value);
        presence=value;
        runtimesteps=0;
      } else {
        Serial.println("No arguments in the OSC message.");
      }
    }
    );

   dac_output_enable(DAC_CHANNEL_1); // Enable DAC channel (GPIO25 or GPIO26)
}

void loop()
{
  OscWiFi.update(); // This is required to keep the OSC listener active
  DW1000Ranging.loop();
}

void newRange()
{
  int i;  //index of this anchor, expecting values 1 to 7
  int index = DW1000Ranging.getDistantDevice()->getShortAddress() & 0x07;
  float range = DW1000Ranging.getDistantDevice()->getRange();
  ranges[index-1]=range;
  return;

}  //end newRange

void newDevice(DW1000Device *device)
{
  Serial.print("Device added: ");
  Serial.println(device->getShortAddress(), HEX);
}

void inactiveDevice(DW1000Device *device)
{
  Serial.print("delete inactive device: ");
  Serial.println(device->getShortAddress(), HEX);
}


void sendMessage(const char *message) {
    udp.beginPacket(host, port);
    udp.write((const uint8_t*)message, strlen(message));  // Ensure to send the whole buffer at once to avoid multiple calls
    udp.endPacket();
}

void OSCTask(void * parameter) {
    while (true) {

        //debug distances
        Serial.print("distances: ");
        Serial.print(ranges[0]);
        Serial.print(" ");
        Serial.print(ranges[1]);
        Serial.print(" ");
        Serial.print(ranges[2]);
        Serial.println(" ");

        OscWiFi.send(host, port, tagid,ranges[0],ranges[1],ranges[2],ranges[3],ranges[4],ranges[5],ranges[6],ranges[7],ranges[8],ranges[9]);

        runtimesteps+=1;
        if (runtimesteps>20){
          //long time since messages from server, let's decrease presence
          presence-=0.01;
          if (presence<0.0){
            presence=0.0;
          }
        }
        delay(50);
    }
}
void soundTask(void * parameter) {
 
  int volume = 26;      // Maximum DAC output for clear clicks

  while (true) {
    int timer = 1000;  // Initialize timer 

    while (timer > 0) {
      // Reduce the timer more significantly if presence is high
      timer -= (int)(2000 * pow(presence, 2)) + 1; // Exponential countdown with higher presence
      delay(100);  // Wait 100ms before next check or action
    }
    // Make a click
    dac_output_voltage(DAC_CHANNEL_1, volume); // Set DAC to the specified volume
    delayMicroseconds(100); // Duration of the click
    dac_output_voltage(DAC_CHANNEL_1, 0);   // Set DAC to zero voltage
  }
}
