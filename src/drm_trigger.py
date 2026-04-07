"""
Trigger Widevine DRM provisioning + key request via frida injection.

This module attaches to a running Android app process and injects Java code
that creates a MediaDrm session, provisions the device (if needed), and
generates a key request. This triggers the Widevine CDM's internal functions
which are hooked by keydive for key extraction.

Must be run AFTER keydive has attached its hooks to the Widevine DRM process.

Uses frida CLI (not the Python API) because the CLI properly initializes
the Java bridge, which is required for MediaDrm injection.
"""
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# JavaScript payload that provisions the device and generates a key request
_JS_PAYLOAD = r"""
Java.perform(function() {
    var UUID = Java.use('java.util.UUID');
    var MediaDrm = Java.use('android.media.MediaDrm');

    var widevineUUID = UUID.fromString("edef8ba9-79d6-4ace-a3c8-27dcd51d21ed");
    console.log("[drm-trigger] Creating MediaDrm...");
    var drm = MediaDrm.$new(widevineUUID);
    console.log("[drm-trigger] Security level: " + drm.getPropertyString("securityLevel"));

    // Try opening a session directly first
    var sessionId = null;
    try {
        sessionId = drm.openSession();
        console.log("[drm-trigger] Session opened (already provisioned)");
    } catch(e) {
        console.log("[drm-trigger] Need provisioning: " + e.message);
        // Device not provisioned - do it now
        try {
            var provReq = drm.getProvisionRequest();
            var reqData = provReq.getData();
            var defaultUrl = provReq.getDefaultUrl();
            console.log("[drm-trigger] Provision request size: " + reqData.length);

            var reqStr = Java.use('java.lang.String').$new(reqData);
            var encoded = Java.use('java.net.URLEncoder').encode(reqStr, "UTF-8");
            var fullUrl = defaultUrl + "&signedRequest=" + encoded;

            var url = Java.use('java.net.URL').$new(fullUrl);
            var conn = Java.cast(url.openConnection(), Java.use('java.net.HttpURLConnection'));
            conn.setRequestMethod("POST");
            conn.setDoInput(true);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);

            var code = conn.getResponseCode();
            console.log("[drm-trigger] Provisioning HTTP " + code);

            if (code === 200) {
                var bis = Java.use('java.io.ByteArrayOutputStream').$new();
                var is = conn.getInputStream();
                var buf = Java.array('byte', new Array(4096).fill(0));
                var len;
                while ((len = is.read(buf)) !== -1) {
                    bis.write(buf, 0, len);
                }
                is.close();
                drm.provideProvisionResponse(bis.toByteArray());
                console.log("[drm-trigger] Device provisioned!");
                sessionId = drm.openSession();
                console.log("[drm-trigger] Session opened after provisioning");
            } else {
                console.log("[drm-trigger] Provisioning failed: HTTP " + code);
            }
        } catch(pe) {
            console.log("[drm-trigger] Provisioning error: " + pe.message);
        }
    }

    // Generate key request if session was opened
    if (sessionId !== null) {
        var pssh = Java.array('byte', [
            0,0,0,52,112,115,115,104,0,0,0,0,
            -19,-17,-117,-87,121,-42,74,-50,-93,-56,39,-36,-43,29,33,-19,
            0,0,0,20,8,1,18,16,
            1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16
        ]);
        try {
            var kr = drm.getKeyRequest(sessionId, pssh, "video/mp4", 1, null);
            console.log("[drm-trigger] Key request generated! Size: " + kr.getData().length);
        } catch(e) {
            console.log("[drm-trigger] getKeyRequest: " + e.message);
        }
        try { drm.closeSession(sessionId); } catch(e) {}
    }

    drm.close();
    console.log("[drm-trigger] Complete!");
});
"""

TARGET_PACKAGE = "Kaltura Device Info"


def _find_frida_bin() -> str:
    """Locate the frida CLI binary (from our venv or PATH)."""
    here = Path(__file__).resolve().parent.parent
    venv_bin = here / "venv-wvd" / "bin" / "frida"
    if venv_bin.exists():
        return str(venv_bin)
    found = shutil.which("frida")
    if found:
        return found
    raise FileNotFoundError("frida CLI not found. Install with: pip install frida-tools")


def run_drm_trigger(serial: str, proc_env: dict = None) -> bool:
    """
    Inject a DRM trigger into the Kaltura app via frida CLI.

    Uses the frida command-line tool (not Python API) because the CLI
    properly initializes the Java bridge needed for MediaDrm calls.

    Args:
        serial: ADB device serial (e.g. 'emulator-5554')
        proc_env: Environment dict (needs ANDROID_ADB_SERVER_ADDRESS for WSL2)

    Returns:
        True if the DRM trigger completed successfully
    """
    frida_bin = _find_frida_bin()

    # Write JS payload to a temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(_JS_PAYLOAD)
        js_path = f.name

    try:
        cmd = [frida_bin, "-U", "-n", TARGET_PACKAGE, "-l", js_path, "-q"]
        logger.info("Running: %s", " ".join(cmd))

        env = proc_env if proc_env else None

        # Retry up to 3 times — the app may not be fully started yet
        import time
        for attempt in range(3):
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )

            output = result.stdout + result.stderr
            if "unable to find process" in output and attempt < 2:
                logger.info("Target not ready yet, retrying in 5s (attempt %d/3)", attempt + 1)
                time.sleep(5)
                continue
            break

        for line in output.strip().split("\n"):
            if line.strip():
                logger.info("  [frida] %s", line.strip())

        success = "Key request generated" in output or "Complete!" in output
        if success:
            logger.info("DRM trigger completed successfully")
        else:
            logger.warning("DRM trigger output: %s", output[:500])

        return success

    except subprocess.TimeoutExpired:
        logger.error("DRM trigger timed out after 60s")
        return False
    except Exception as e:
        logger.error("DRM trigger failed: %s", e)
        return False
    finally:
        Path(js_path).unlink(missing_ok=True)
