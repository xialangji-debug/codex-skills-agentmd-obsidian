"""Select a live ASR transport and pass one verified package to the flash owner."""

import argparse
import importlib.util
import json
import re
from pathlib import Path


# These are USB transport profiles, not board/product compatibility claims.
NORMAL_USB = "VID_2ECC&PID_3010"
DOWNLOAD_USB = "VID_2ECC&PID_3004"


def select_transport(owner, devices, requested_port=None):
    """Resolve only interfaces belonging to the one current physical target."""
    summary = owner.summarize_asr_devices(devices)
    ids = summary.get("physicalDeviceIds") or []
    targets = summary.get("targets") or []

    def blocked(reason):
        return {"status": "BLOCKED", "stage": "transport-selection",
                "error": reason, "devices": summary}

    if len(ids) != 1 or len(targets) != 1:
        return blocked("Exactly one physical ASR USB target is required; found %d" % len(ids))
    target = targets[0]
    physical_id = str(target.get("physicalDeviceId") or "")
    if physical_id.lower() != str(ids[0]).lower():
        return blocked("ASR target and physical identity do not agree")
    roots = [d for d in devices if str(d.get("DeviceID") or "").lower() == physical_id.lower()]

    def healthy(device):
        return (str(device.get("Status") or "").upper() == "OK"
                and device.get("ConfigManagerErrorCode") in (None, 0, "0"))

    if len(roots) != 1 or not healthy(roots[0]):
        return blocked("The selected ASR physical USB device is not healthy/present")
    port = str(requested_port or "").strip().upper()
    if port and not re.fullmatch(r"COM\d+", port):
        return blocked("Port must be one current ASR interface, for example COM7")
    vid_pid = str(target.get("vidPid") or "").upper()
    if vid_pid == NORMAL_USB:
        ports = target.get("mainModemPorts") or []
        if len(ports) != 1:
            return blocked("Normal mode requires one main Modem interface of the selected target")
        detected = ports[0].upper()
        if port and port != detected:
            return blocked("Requested port %s is not this target's current main Modem port %s" % (port, detected))
        interfaces = [d for d in devices
                      if str(d.get("ParentDeviceID") or "").lower() == physical_id.lower()
                      and owner.port_from_name(d.get("Name")) == detected
                      and re.search(r"VID_2ECC&PID_3010&MI_02", str(d.get("DeviceID") or ""), re.I)]
        if len(interfaces) != 1 or not healthy(interfaces[0]):
            return blocked("The selected main Modem interface is not healthy/present")
        mode, ports, usb_only, at_fallback = "normal-at", [detected], False, True
    elif vid_pid == DOWNLOAD_USB:
        # In this owner's current inventory, a boot-ROM COM device can be the
        # physical root itself rather than a child in target.downloadPorts.
        ports = set(target.get("downloadPorts") or [])
        root_port = owner.port_from_name(roots[0].get("Name"))
        if root_port:
            ports.add(root_port)
        if port and port not in ports:
            return blocked("Requested port does not belong to the current ASR download target")
        mode, ports, usb_only, at_fallback = "download-usb", [], True, False
    else:
        return blocked("No automatic transport profile is registered for %s" % (vid_pid or "this USB identity"))
    return {"status": "READY", "mode": mode, "target": target,
            "requestedPort": port or None, "ports": ports,
            "usbOnly": usb_only, "atFallback": at_fallback,
            "expectedPhysicalDeviceId": physical_id}


def observe_normal_usb(selection, post_status):
    """Reuse the owner's final snapshot; USB enumeration is not a boot test."""
    observation = {"status": "NOT_OBSERVED", "functionalVerification": "PENDING"}
    targets = post_status.get("asrTargets") or []
    if len(targets) != 1:
        return observation
    after = targets[0]
    if str(after.get("vidPid") or "").upper() != NORMAL_USB or not after.get("complete"):
        return observation
    before = selection["target"]
    old_paths = {str(p).lower() for p in before.get("locationPaths", []) if p}
    new_paths = {str(p).lower() for p in after.get("locationPaths", []) if p}
    same_id = str(after.get("physicalDeviceId") or "").lower() == selection["expectedPhysicalDeviceId"].lower()
    if old_paths and new_paths and old_paths.isdisjoint(new_paths):
        return dict(observation, status="UNVERIFIED", reason="USB location changed")
    if not same_id and not old_paths.intersection(new_paths):
        return dict(observation, status="UNVERIFIED", reason="Normal USB target cannot be correlated with the flashed target")
    return dict(observation, status="NORMAL_USB_OBSERVED",
                identityBasis="physical-id" if same_id else "usb-location",
                mainModemPorts=after.get("mainModemPorts") or [])


def flash_once(owner, args):
    selection = select_transport(owner, owner.get_asr_devices(), args.port)
    if selection["status"] != "READY":
        return selection
    result = owner.flash({
        "releasePackage": str(Path(args.package).resolve()),
        "expectedPackageSha256": args.sha256,
        "adownloadPath": args.adownload,
        "ports": selection["ports"],
        "usbOnly": selection["usbOnly"],
        "atFallback": selection["atFallback"],
        # The owner re-enumerates and checks this pin immediately before its
        # existing package/process/transport gates. Never retry another target.
        "expectedPhysicalDeviceId": selection["expectedPhysicalDeviceId"],
        "timeoutSec": args.timeout_sec,
        "killExistingAdownload": False,
        "closeCatstudio": False,
        "closeAbootGui": False,
    })
    result["transportSelection"] = selection
    result.setdefault("stage", "flash-owner")
    if result.get("status") == "SUCCEEDED":
        result["verificationLevel"] = "FLASH_PASSED"
        result["bootObservation"] = observe_normal_usb(selection, result.get("postStatus") or {})
    # TIMEOUT/UNKNOWN/FAILED/BLOCKED remain terminal for this invocation. The
    # owner retains its process exit, terminal events, log and timeout evidence.
    return result


def timeout_seconds(value):
    value = int(value)
    if not 1 <= value <= 3600:
        raise argparse.ArgumentTypeError("timeout must be between 1 and 3600 seconds")
    return value


def load_aboot():
    path = Path.home() / "plugins/aboot-download/scripts/aboot_download_mcp.py"
    if not path.is_file():
        raise RuntimeError(f"Installed aboot-download implementation is missing: {path}")
    spec = importlib.util.spec_from_file_location("local_verified_aboot", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--adownload", required=True)
    parser.add_argument("--port")
    parser.add_argument("--timeout-sec", type=timeout_seconds, default=900)
    parser.add_argument("--result-file", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        owner = load_aboot()
        result = flash_once(owner, args)
    except Exception as exc:
        result = {"status": "ERROR", "stage": "flash-owner", "error": str(exc)}
    args.result_file.parent.mkdir(parents=True, exist_ok=True)
    args.result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "SUCCEEDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
