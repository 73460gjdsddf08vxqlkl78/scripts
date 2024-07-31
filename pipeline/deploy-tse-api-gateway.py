#!/usr/bin/env python3
import argparse
import os
import sys
from tencentcloud.common import credential
from tencentcloud.tse.v20201207 import tse_client, models

###########################################################
# API Gateway Config
###########################################################

API_GATEWAY_REGION = os.environ["API_GATEWAY_REGION"]
API_GATEWAY_ID = os.environ["API_GATEWAY_ID"]

###########################################################
# Setup Tencent Cloud Client
###########################################################
TENCENT_CLOUD_SECRET_ID = os.environ["TENCENT_CLOUD_SECRET_ID"]
TENCENT_CLOUD_SECRET_KEY = os.environ["TENCENT_CLOUD_SECRET_KEY"]

TENCENT_API_GATEWAY_CLIENT = tse_client.TseClient(
    credential.Credential(
        TENCENT_CLOUD_SECRET_ID,
        TENCENT_CLOUD_SECRET_KEY,
    ),
    API_GATEWAY_REGION,
)


def update_cos_backend(api: models.DescribeApiResponse, args: argparse.Namespace):
    request = models.ModifyApiRequest()
    request.from_json_string(api.Result.to_json_string())
    request.ServiceType = "COS"
    request.ServiceConfig = models.ServiceConfig()
    request.ServiceConfig.from_json_string(
        f"""
        {{
            "CosConfig": {{
                "Action": "GetObject",
                "BucketName": "{args.bucket}",
                "Authorization": true,
                "PathMatchMode": "FullPath"
            }},
            "Path": "{args.path}"
        }}
        """
    )
    response = TENCENT_API_GATEWAY_CLIENT.ModifyApi(request)
    print(f"[*] Updated API Gateway Config: {response}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy TSE API Gateway")
    parser.add_argument("--name", type=str, required=True, help="The name of API Gateway service")
    parser.add_argument("--protocol", type=str, default="https", choices=["http", "https", "tcp", "udp"], help="The protocol of API Gateway service")
    parser.add_argument("--path", type=str, default="/", help="The path of API Gateway service")

    parser.add_argument("--type", type=str, required=True, choices=["Kubernetes", "Registry", "IPList", "HostIP", "Scf"], help="The upstream type of API Gateway service")
    group_hostip = parser.add_argument_group("HostIP")
    group_hostip.add_argument("--host", type=str, help="The IP or host of upstream server.")
    group_hostip.add_argument("--port", type=int, help="The port of upstream server.")
    args = parser.parse_args()

    # Update API Gateway service.
    request = models.ModifyCloudNativeAPIGatewayServiceRequest()
    request.GatewayId = API_GATEWAY_ID
    request.Name = args.name
    request.Protocol = args.protocol
    request.Path = args.path

    request.UpstreamType = args.type
    request.UpstreamInfo = models.KongUpstreamInfo()
    if args.type == "HostIP":
        request.UpstreamInfo.Host = args.host
        request.UpstreamInfo.Port = args.port
    else:
        # TODO: Support more upstream types.
        raise Exception("Unsupported upstream type.")

    response = TENCENT_API_GATEWAY_CLIENT.ModifyCloudNativeAPIGatewayService(request)
    print(f"[*] Released API Gateway: {response}")