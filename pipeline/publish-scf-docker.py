#!/usr/bin/env python3
import argparse
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

def publish(image_repo: str, image_tag: str) -> str:
    # Update $LATEST codes.
    req = new_default_request(models.UpdateFunctionCodeRequest())
    req.Code = models.Code()
    req.Code.ImageConfig = models.ImageConfig()
    req.Code.ImageConfig.ImageType = "personal"
    req.Code.ImageConfig.ImageUri = f"{image_repo}:{image_tag}"
    resp = TENCENT_SCF_CLIENT.UpdateFunctionCode(req)
    print(f"[*] Updated SCF function {SCF_FUNCTION} with image {image_repo}:{image_tag}. Response: {resp}", file=sys.stderr)

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
    parser = argparse.ArgumentParser(description="Deploy SCF with Docker image.")
    parser.add_argument("image_repo", help="Docker image repository to deploy.")
    parser.add_argument("image_tag", help="Docker image tag to deploy.")
    args = parser.parse_args()

    # Publish docker image.
    version = publish(args.image_repo, args.image_tag)
    print(version, end="", file=sys.stdout)