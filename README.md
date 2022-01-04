# EloDeck
Use a MIDI controller device as a launchpad for apps or any commands, or a streaming deck.Using EloDeck one can configure the MIDI controller knobs and buttons and use it to launch programms or actions.

## Use case
[Behringer Xtouch Mini controller](https://www.behringer.com/product.html?modelCode=P0B3M) is a nice and responsive MIDI device with a slider, buttons, pots and LEDs.

<img src="https://mediadl.musictribe.com/media/PLM/data/images/products/P0B3M/2000Wx2000H/X-TOUCH-MINI_P0B3M_Top_XL.png" width="50%">

I am using it as a launchpad for various tasks at my computer:

* Selecting audio sources - speakers, headphones, playback and pause, volume control
* Controlling [OBS](https://obsproject.com/): start, pause and stop recording.
* Selecting scenes in OBS.
* Controlling color temperature for my webcam it real time
* Launching arbitrary commands and programs

## How

This project is written in Python for Linux environment and takes a configuration file in YAML that describes the MIDI device and the assignment of the commands to the MIDI events. Essentially, you could use any MIDI contriller and write a mapping from its events to the commands you desire.

The project is monitoring system for USB Midi device connections. You can specify which device to monitor. If the device gets reconnected, the program monitor the system events for reconnection of any MIDI device and restarts the process as soon as the device is connected again.

## Support

Currently I have added support for the following MIDI controllers:
* [Behringer Xtouch Mini controller](https://www.behringer.com/product.html?modelCode=P0B3M)
* [Akai LPD8](https://www.akaipro.com/lpd8)

Send me a device and I will add support for it :)

## License

This project is under MIT license.
