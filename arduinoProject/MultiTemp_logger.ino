#include <DS18B20.h>

DS18B20 ds(16);

char DeviceAmount = 0;
void setup() {
//initialize Serial 
  Serial.begin(115200);
  Serial.print("Devices: ");
//get number of Temp sensors
  DeviceAmount = ds.getNumberOfDevices();
  Serial.println(DeviceAmount);
  Serial.println();
//initialize DS Temp
  ds.setResolution(12);
//initialize TFT
}
char FirstLoop =1, n=0;
char buff[16];
float Temps;
void loop() {
  n=0;
  while (ds.selectNext()) {
    Temps = ds.getTempC();
    if(!FirstLoop)Serial.print(",");
    Serial.print(Temps);
    FirstLoop = 0;
  }
  FirstLoop =1;
  Serial.println("");
  delay(1000);
}
