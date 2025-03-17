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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy TSE API Gateway")
    parser.add_argument("--id", type=str, required=True, help="The ID of API Gateway service")
    parser.add_argument("--name", type=str, required=True, help="The name of API Gateway service")
    parser.add_argument("--protocol", type=str, default="https", choices=["http", "https", "tcp", "udp"], help="The protocol of API Gateway service")
    parser.add_argument("--path", type=str, default="/", help="The path of API Gateway service")
    parser.add_argument("--timeout", type=int, default=60000, help="The timeout of upstream server (milliseconds)")
    parser.add_argument("--retries", type=int, default=0, help="The number of retries for upstream server")

    parser.add_argument("--type", type=str, required=True, choices=["Kubernetes", "Registry", "IPList", "HostIP", "Scf"], help="The type of API Gateway upstream service")
    group_hostip = parser.add_argument_group("HostIP")
    group_hostip.add_argument("--host", type=str, help="The IP or host of upstream server.")
    group_hostip.add_argument("--port", type=int, help="The port of upstream server.")
    args = parser.parse_args()

    # Update API Gateway service.
    request = models.ModifyCloudNativeAPIGatewayServiceRequest()
    request.GatewayId = API_GATEWAY_ID
    request.ID = args.id
    request.Name = args.name
    request.Protocol = args.protocol
    request.Path = args.path
    request.Timeout = args.timeout
    request.Retries = args.retries

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