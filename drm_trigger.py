"""Trigger Widevine DRM via frida injection into an Android process."""
import frida
import time

DEVICE_SERIAL = "emulator-5554"
TARGET_PACKAGE = "com.kaltura.kalturadeviceinfo"

JS_PAYLOAD = r"""
setTimeout(function() {
    Java.perform(function() {
        var UUID = Java.use('java.util.UUID');
        var MediaDrm = Java.use('android.media.MediaDrm');

        var widevineUUID = UUID.fromString("edef8ba9-79d6-4ace-a3c8-27dcd51d21ed");
        console.log("[*] Creating MediaDrm...");
        var drm = MediaDrm.$new(widevineUUID);
        console.log("[*] Security level: " + drm.getPropertyString("securityLevel"));

        console.log("[*] Opening session...");
        var sessionId = drm.openSession();
        console.log("[*] Session opened, ID len: " + sessionId.length);

        var pssh = Java.array('byte', [
            0x00,0x00,0x00,0x34,0x70,0x73,0x73,0x68,
            0x00,0x00,0x00,0x00,-19,-17,-117,-87,
            0x79,-42,0x4a,-50,-93,-56,0x27,-36,
            -43,0x1d,0x21,-19,0x00,0x00,0x00,0x14,
            0x08,0x01,0x12,0x10,0x01,0x02,0x03,0x04,
            0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0x0c,
            0x0d,0x0e,0x0f,0x10
        ]);

        console.log("[*] Generating key request...");
        try {
            var keyReq = drm.getKeyRequest(sessionId, pssh, "video/mp4", 1, null);
            console.log("[*] Key request generated! Size: " + keyReq.getData().length);
            console.log("[*] Default URL: " + keyReq.getDefaultUrl());
        } catch(e) {
            console.log("[!] getKeyRequest error: " + e);
        }

        try { drm.closeSession(sessionId); } catch(e) {}
        console.log("[*] DRM trigger complete!");
    });
}, 3000);
"""

def on_message(message, data):
    if message['type'] == 'send':
        print(f"[frida] {message['payload']}")
    elif message['type'] == 'error':
        print(f"[frida-error] {message['description']}")
    else:
        print(f"[frida-{message['type']}] {message}")

def main():
    device = frida.get_device(DEVICE_SERIAL)
    print(f"[+] Connected to {device}")

    pid = None
    for proc in device.enumerate_processes():
        if TARGET_PACKAGE in proc.name:
            pid = proc.pid
            break

    if not pid:
        print(f"[*] Spawning {TARGET_PACKAGE}...")
        pid = device.spawn(TARGET_PACKAGE)
        device.resume(pid)
        time.sleep(3)

    print(f"[+] Attaching to PID {pid}")
    session = device.attach(pid)
    script = session.create_script(JS_PAYLOAD)
    script.on('message', on_message)
    script.load()
    print("[+] Waiting for DRM trigger...")
    time.sleep(15)
    print("[+] Done")

if __name__ == "__main__":
    main()
