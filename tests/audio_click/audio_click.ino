#include "driver/dac.h"

void setup() {
  dac_output_enable(DAC_CHANNEL_1); // Enable DAC channel (GPIO25 or GPIO26)
}

void loop() {
  // Generate a click
  // Maximize the DAC output
for (int i = 0; i < 255; i++) {
  dac_output_voltage(DAC_CHANNEL_1, 255); // Use maximum voltage for the pulse
  delayMicroseconds(2); // Short burst
}
for (int i = 255; i >= 0; i--) {
  dac_output_voltage(DAC_CHANNEL_1, 0); // Drop to zero quickly
  delayMicroseconds(2); // Short burst
}
  
  // Wait to simulate random detection intervals
  delay(random(100, 1000)); // Random delay between clicks
}

