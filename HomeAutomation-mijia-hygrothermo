# HomeAutomation-mijia-hygrothermo
A quick/dirty hack to connect xiaomi mijia devices and collect data

This project is based on the following components:
- raspberry pi zero + raspbian
  https://www.raspberrypi.org/blog/zero-wh/
  
  Note1: The zero variant has a much better signal range than what is on rasp3b or rasp4
  
  Note2: You may want to consider using an addon bluetooth module (e.g. usb based) to gain more range and more clearly receive end point broadcasts.
  https://shop.espruino.com/accessories/usb-bluetooth
  
  Note3: Different BLE standards have different capabilities and ranges. 
  
  https://blog.nordicsemi.com/getconnected/things-you-should-know-about-bluetooth-range
  
  https://blog.nordicsemi.com/getconnected/tested-by-nordic-bluetooth-long-range
  
- xiaomi mijia LYWSD03MMC devices
- 
  https://tinyl.io/4Y7f

  note1: the original firmware is not optimal. an alternative optimized firmware is available at:
  
  https://www.youtube.com/watch?v=NXKzFG61lNs
  
  https://github.com/pvvx/ATC_MiThermometer
  
  note2: you will need to remove the battery twice during the process of updating the firmware. 
  
  note3: you will need to enable chrome://flags/#enable-experimental-web-platform-features for the OTA firmware update to function (disable right after!)
  
  note4: when scanning to upgrade the firmware, do not change desktops of windows as this can interrupt and cancel the operation!
  
  note5: link to OTA flash mijia devices: https://pvvx.github.io/ATC_MiThermometer/TelinkMiFlasher.html
  
  
- bluetooth support for raspberry pi
  #apt install bluetooth pi-bluetooth bluez blueman  
  
  note1: reboot the raspberry pi after the installation in order to recognize the native bluetooth device
  
  note2: bluetoothctl utility is not reliable and wont necessarily always display the BLE devices. alternatively you can use "gatttool" and "hcitool lescan".

- There currently are python scripts and tools that enable to collect data from the devices. I opted not to use this for the following reasons:
  - i want to process the data 
  - i want to use the custom firmware and leverage the broadcast approach to save energy
  - i want to create own light weight graphing (probably mrtg, rrdtool, gnuplot or then again influxdb, havent decided at the time of writing)

alternatively, you can use the native firmware and the following to directly connect from home assistant: 

https://www.home-assistant.io/integrations/mitemp_bt/ 

https://prosindo.com/blog/2020/04/23/monitor-temperatures-using-bluetooth-xiaomi-mijia-thermostat-mj_ht_v1-linux-python-bash/

http://www.d0wn.com/using-bash-and-gatttool-to-get-readings-from-xiaomi-mijia-lywsd03mmc-temperature-humidity-sensor/

https://github.com/belkop-ghb/LYWSD03MMC/blob/master/readSensors.sh

https://sarajarvi.org/mijia-bt-sensorit/

- python 3.7
  this python version is required by MiTemperature2. to install:
  #apt install python3 python3-pip
  
  #pip3 install bluepy requests
  
  #apt install bluetooth libbluetooth-dev
  
  #pip3 install pybluez
  
  
- clone the github source the code with which to connect to the mijia devices:  
  mkdir -p /opt/mijia/
  cd /opt/mijia
  git clone https://github.com/JsBergbau/MiTemperature2.git
  
- install influxdb
  #apt install influxdb

- install lighttpd for other purposes
  #apt install lighttpd
