#!/usr/bin/env python3
"""Read-only Oracle San Jose Always Free compute capacity checker.

Uses OCI API request signatures via OpenSSL, not the heavyweight OCI SDK.
No instance creation, no login-token export, no paid-shape requests.
"""
import base64
import configparser
import datetime as dt
import email.utils
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REGION = "us-sanjose-1"
# Both Always Free shapes, including every whole-GB A1 configuration
# within the currently documented 2 OCPU / 12 GB Always Free total.
FREE_SHAPES = [("VM.Standard.E2.1.Micro", None)] + [
    ("VM.Standard.A1.Flex", (cpus, ram_gb))
    for cpus in (1, 2)
    for ram_gb in range(cpus, 13)
]



class OCIError(Exception):
    pass


def load_oci_config():
    confpath = Path(os.environ.get("OCI_CONFIG_FILE", "~/.oci/config")).expanduser()
    if not confpath.is_file():
        raise OCIError(
            f"OCI API configuration not found: {confpath}\n"
            "Create an OCI API signing key in the Oracle console, and put the "
            "Oracle-generated config snippet into ~/.oci/config."
        )
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(str(confpath))
    profile = os.environ.get("OCI_PROFILE", "DEFAULT")
    if profile not in parser:
        raise OCIError(f"OCI profile [{profile}] not found in {confpath}")
    c = parser[profile]
    for field in ("tenancy", "user", "fingerprint", "key_file"):
        if not c.get(field):
            raise OCIError(f"Missing '{field}' from OCI config profile [{profile}]")
    # Only sign using the key file that Oracle's own config references.
    key = Path(os.path.expandvars(os.path.expanduser(c["key_file"])))
    if not key.is_absolute():
        key = confpath.parent / key
    if not key.is_file():
        raise OCIError(f"API signing key file not found: {key}")
    if not c["tenancy"].startswith("ocid1.tenancy.") or not c["user"].startswith("ocid1.user."):
        raise OCIError("Invalid-looking tenancy or user OCID in OCI configuration")
    if not re.fullmatch(r"[0-9a-fA-F:]{47}", c["fingerprint"]):
        raise OCIError("OCI API key fingerprint should be 16 colon-separated hex bytes")
    if not shutil.which("openssl"):
        raise OCIError("OpenSSL is missing. Run: apk add openssl")
    return c, key


def api_call(config, keypath, host, method, route, payload=None):
    if host not in (f"identity.{REGION}.oci.oraclecloud.com", f"iaas.{REGION}.oraclecloud.com"):
        raise OCIError("Refusing API call to unrecognized, non-Oracle host")
    if method not in ("GET", "POST") or not route.startswith("/20160918/"):
        raise OCIError("Refusing unexpected API method or path")
    date = email.utils.formatdate(usegmt=True)
    fields = ["(request-target)", "date", "host"]
    signed = [f"(request-target): {method.lower()} {route}", f"date: {date}", f"host: {host}"]
    headers = {"date": date, "host": host, "accept": "application/json"}
    data = None
    if method == "POST":
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        digest = base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")
        post_fields = [
            ("x-content-sha256", digest),
            ("content-type", "application/json"),
            ("content-length", str(len(data))),
        ]
        for name, value in post_fields:
            fields.append(name)
            signed.append(f"{name}: {value}")
            headers[name] = value
    signing_string = "\n".join(signed).encode("utf-8")
    args = ["openssl", "dgst", "-sha256", "-sign", str(keypath)]
    if os.environ.get("OCI_KEY_PASSPHRASE"):
        args += ["-passin", "env:OCI_KEY_PASSPHRASE"]
    signature_result = subprocess.run(args, input=signing_string, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if signature_result.returncode:
        raise OCIError("OpenSSL could not use the signing key. Confirm its location and passphrase.")
    signature = base64.b64encode(signature_result.stdout).decode("ascii")
    key_id = "/".join((config["tenancy"], config["user"], config["fingerprint"]))
    headers["authorization"] = (
        'Signature version="1",keyId="' + key_id
        + '",algorithm="rsa-sha256",headers="' + " ".join(fields)
        + '",signature="' + signature + '"'
    )
    request = urllib.request.Request("https://" + host + route, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error = json.loads(exc.read().decode("utf-8"))
            code, message = error.get("code", "Unknown"), error.get("message", "")
        except (ValueError, UnicodeError):
            code, message = "Unknown", "Could not parse Oracle's API error response"
        raise OCIError(f"Oracle API HTTP {exc.code} ({code}): {message[:350]}") from None
    except urllib.error.URLError as exc:
        raise OCIError("Network/TLS connection to Oracle failed. Check iSH internet and clock.") from None


def shape_label(shape, cfg):
    if cfg is None:
        return "AMD E2.1.Micro (1 GB RAM)"
    cpu, mem = cfg
    return f"Ampere A1.Flex ({cpu} OCPU, {mem} GB RAM)"


def query_shape(config, key, domain, shape, cfg):
    availability = {"instanceShape": shape}
    if cfg is not None:
        cpu, mem = cfg
        availability["instanceShapeConfig"] = {"ocpus": float(cpu), "memoryInGBs": float(mem)}
    body = {
        "compartmentId": config["tenancy"],
        "availabilityDomain": domain,
        "shapeAvailabilities": [availability],
    }
    return api_call(config, key, f"iaas.{REGION}.oraclecloud.com", "POST", "/20160918/computeCapacityReports", body)


def main():
    if "--self-test" in sys.argv:
        assert len(FREE_SHAPES) == 24
        assert set(shape for shape, _ in FREE_SHAPES) == {"VM.Standard.A1.Flex", "VM.Standard.E2.1.Micro"}
        assert all((cfg is None or (cfg[0] in (1, 2) and cfg[0] <= cfg[1] <= 12)) for _, cfg in FREE_SHAPES)
        print("PASS: only Always Free shape families and bounded A1 configurations")
        return
    config, key = load_oci_config()
    print("Oracle Cloud — San Jose Always Free capacity report")
    print("Region: us-sanjose-1 | no VM creation, no billing actions")
    print("A1 Always Free pool: 2 OCPUs / 12 GB total (current Oracle docs)")
    print("E2 micro: up to 2 VMs; block + boot storage total: 200 GB")
    print("Report status is momentary capacity, not an instance reservation.\n")
    identity = f"identity.{REGION}.oci.oraclecloud.com"
    # Oracle Always Free compute is only in tenancy's home region.
    try:
        route = "/20160918/tenancies/" + urllib.parse.quote(config["tenancy"], safe="") + "/regionSubscriptions"
        subs = api_call(config, key, identity, "GET", route)
        if isinstance(subs, list):
            home = [s.get("regionName") for s in subs if s.get("isHomeRegion")]
            print("Home region:", ", ".join(home) if home else "not returned")
            if home and REGION not in home:
                print("WARNING: San Jose is not your home region; instances there may not be Always Free!\n")
    except OCIError as exc:
        print("Home-region lookup unavailable:", exc)
    ads_route = "/20160918/availabilityDomains?" + urllib.parse.urlencode({"compartmentId": config["tenancy"]})
    ads = api_call(config, key, identity, "GET", ads_route)
    if not isinstance(ads, list):
        raise OCIError("OCI returned an unexpected availability-domain response")
    domains = [ad.get("name", "") for ad in ads if ad.get("name")]
    if not domains:
        raise OCIError("No availability domains returned for this tenancy in San Jose")
    print("Availability domain(s):", ", ".join(domains))
    print("Reading only — both Always Free shapes and all whole-GB A1 sizes within the free pool.\n")
    for domain in domains:
        print("===", domain, "===")
        for shape, cfg in FREE_SHAPES:
            title = shape_label(shape, cfg)
            try:
                result = query_shape(config, key, domain, shape, cfg)
                entries = result.get("shapeAvailabilities", [])
                if not entries:
                    msg = "No capacity information returned"
                else:
                    parts = []
                    for row in entries:
                        state = row.get("availabilityStatus", "UNKNOWN")
                        count = row.get("availableCount", "?")
                        parts.append(state + " (reported count " + str(count) + ")")
                    msg = "; ".join(parts)
                print(f"  {title}: {msg}")
            except OCIError as exc:
                print(f"  {title}: CHECK UNAVAILABLE — {exc}")
                if "HTTP 401" in str(exc) or "HTTP 403" in str(exc):
                    raise OCIError("Account authentication or capacity-report permission denied. Ask your OCI admin about the 'manage compute-capacity-reports in tenancy' policy. No VM was created.") from None
        print()
    print("Done. AVAILABLE is not a promise that a free instance will launch:")
    print("OCI Always Free quotas, account limits, subnet/boot volume and placement still apply.")
    print("Do not select paid shapes or create a VM based on this report alone.")


if __name__ == "__main__":
    try:
        main()
    except OCIError as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)