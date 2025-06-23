Dump NUX tutorial
---
NUX is **specific to device model** (Eureka, Hollywood etc) so here are the commands to dump from your device.

Run the following:
```console
adb shell pm path com.oculus.firsttimenux
```
This will give you an output starting with `package:/system_ext/app...`

Remove the bit starting with `package:` and put it into `adb pull`, (i.e. `adb pull /system_ext/app...`).
This copies the APK to the current directory the shell is in. You can use a fancy APK viewer to look into it or just rename extension to `.zip` to open it up.
