#!/usr/bin/env python3
import argparse
import base64
import os
import sys
import time
from tencentcloud.common import credential
from tencentcloud.scf.v20180416 import scf_client, models


###########################################################
# SCF Config
###########################################################
SCF_REGION = os.environ["SCF_REGION"]
SCF_NAMESPACE = os.environ["SCF_NAMESPACE"]
SCF_FUNCTION = os.environ["SCF_FUNCTION"]

###########################################################
# Setup Tencent Cloud Client
###########################################################
TENCENT_CLOUD_SECRET_ID = os.environ["TENCENT_CLOUD_SECRET_ID"]
TENCENT_CLOUD_SECRET_KEY = os.environ["TENCENT_CLOUD_SECRET_KEY"]

TENCENT_SCF_CLIENT = scf_client.ScfClient(
    credential.Credential(
        TENCENT_CLOUD_SECRET_ID,
        TENCENT_CLOUD_SECRET_KEY,
    ),
    SCF_REGION,
)


def new_default_request(req):
    req.Namespace = SCF_NAMESPACE
    req.FunctionName = SCF_FUNCTION
    return req

def wait_until(version: str, status: str):
    while True:
        req = new_default_request(models.GetFunctionRequest())
        req.Qualifier = version
        req.ShowCode = "FALSE"
        resp = TENCENT_SCF_CLIENT.GetFunction(req)
        if resp.Status == status:
            return
        time.sleep(1)

def publish(file_content: str) -> str:
    # Update $LATEST codes.
    req = new_default_request(models.UpdateFunctionCodeRequest())
    req.ZipFile = file_content
    resp = TENCENT_SCF_CLIENT.UpdateFunctionCode(req)
    print(f"[*] Updated SCF function {SCF_FUNCTION}. Response: {resp}", file=sys.stderr)

    # Wait until $LATEST version online.
    wait_until("$LATEST", "Active")

    # Publish $LATEST version.
    req = new_default_request(models.PublishVersionRequest())
    resp = TENCENT_SCF_CLIENT.PublishVersion(req)
    print(f"[*] Published SCF version: {resp.FunctionVersion}. Response: {resp}", file=sys.stderr)

    # Wait until published version online.
    wait_until(resp.FunctionVersion, "Active")

    return resp.FunctionVersion

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy SCF with ZIP package.")
    parser.add_argument("file", help="The path of ZIP package.", type=str)
    args = parser.parse_args()

    # Check file size.
    if os.path.getsize(args.file) > 20 * 1024 * 1024:
        print("[!] The size of ZIP package should be less than 20MB.", file=sys.stderr)
        exit(1)

    # Encode file to base64.
    with open(args.file, "rb") as f:
        file_content = base64.b64encode(f.read()).decode("utf-8")

    # Deploy SCF.
    version = publish(file_content)
    print(version, end="", file=sys.stdout)