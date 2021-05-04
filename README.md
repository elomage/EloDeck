# EloDeck
Use a MIDI controller device as a launchpad for apps or any commands, or a streaming deck.

## Use case
There is a Behringer Xtouch Mini controller with buttons, pots and LEDs. I am using it as a launchpad for various tasks at my computer:

* Selecting audio sources - speakers, headphones, playback and pause, volume control
* Controlling OBS: start, pause and stop recording.
* Selecting scenes in OBS.
* Controlling color temperature for my webcam it real time
* Launching arbitrary commands and programs

## How

This project is written in Python and takes a configuration file in YAML that describes the MIDI device and the assignment of the commands to the MIDI events. Essentially, you could use any MIDI contriller and write a mapping from its events to the commands you desire.

The project is monitoring system for USB Midi device connections. You can specify which device to monitor. If the device gets reconnected, the program monitor the system events for reconnection of any MIDI device and restarts the process as soon as the device is connected again.

## License

This project is under MIT license.
