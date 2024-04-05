#!/usr/bin/env python3
import base64
import os
import time
from tencentcloud.common import credential
from tencentcloud.scf.v20180416 import scf_client, models


###########################################################
# SCF Config
###########################################################

SCF_REGION = os.environ["SCF_REGION"]
SCF_NAMESPACE = os.environ["SCF_NAMESPACE"]
SCF_FUNCTION = os.environ["SCF_FUNCTION"]
SCF_ENABLE_CONCURRENCY = os.environ.get("SCF_ENABEL_CONCURRENCY", "false").lower() == "true"
SCF_DEFAULT_CONCURRENCY = int(os.environ.get("SCF_DEFAULT_CONCURRENCY", "1"))

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
    print(f"[*] Updated SCF function {SCF_FUNCTION}. Response: {resp}")

    # Wait until $LATEST version online.
    wait_until("$LATEST", "Active")

    # Publish $LATEST version.
    req = new_default_request(models.PublishVersionRequest())
    resp = TENCENT_SCF_CLIENT.PublishVersion(req)
    print(f"[*] Published SCF version: {resp.FunctionVersion}. Response: {resp}")

    return resp.FunctionVersion

def deploy(version: str):
    # Wait until version online.
    wait_until(version, "Active")

    # Allocate provisioned concurrency.
    if SCF_ENABLE_CONCURRENCY:
        req = new_default_request(models.PutProvisionedConcurrencyConfigRequest())
        req.Qualifier = version
        req.VersionProvisionedConcurrencyNum = SCF_DEFAULT_CONCURRENCY
        resp = TENCENT_SCF_CLIENT.PutProvisionedConcurrencyConfig(req)
        print(f"[*] Updated provisioned concurrency: {resp}")

    # Update traffic config.
    req = new_default_request(models.UpdateAliasRequest())
    req.Name = "$DEFAULT"
    req.FunctionVersion = version
    resp = TENCENT_SCF_CLIENT.UpdateAlias(req)
    print(f"[*] Updated $DEFAULT traffic: {resp}")

def cleanup(version: str):
    # Delete outdated provisioned concurrency allocations.
    req = new_default_request(models.GetProvisionedConcurrencyConfigRequest())    
    provision = TENCENT_SCF_CLIENT.GetProvisionedConcurrencyConfig(req)
    for allocation in provision.Allocated:
        if allocation.Qualifier == version:
            continue
        req = new_default_request(models.DeleteProvisionedConcurrencyConfigRequest())
        req.Qualifier = allocation.Qualifier
        deleted = TENCENT_SCF_CLIENT.DeleteProvisionedConcurrencyConfig(req)
        print(f"[*] Deleted outdated provisioned concurrency allocation for version {allocation.Qualifier}: {deleted}")

    # Delete outdated versions.
    req = new_default_request(models.ListVersionByFunctionRequest())
    versions = TENCENT_SCF_CLIENT.ListVersionByFunction(req)
    for v in versions.FunctionVersion:
        if v == "$LATEST" or v == version:
            continue
        req = new_default_request(models.DeleteFunctionRequest())
        req.Qualifier = v
        deleted = TENCENT_SCF_CLIENT.DeleteFunction(req)
        print(f"[*] Deleted outdated version {v}: {deleted}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Deploy SCF with ZIP package.")
    parser.add_argument("file", help="The path of ZIP package.", type=str)
    args = parser.parse_args()

    # Check file size.
    if os.path.getsize(args.file) > 20 * 1024 * 1024:
        print("[!] The size of ZIP package should be less than 20MB.")
        exit(1)

    # Encode file to base64.
    with open(args.file, "rb") as f:
        file_content = base64.b64encode(f.read()).decode("utf-8")

    # Deploy SCF.
    version = publish(file_content)
    deploy(version)
    cleanup(version)