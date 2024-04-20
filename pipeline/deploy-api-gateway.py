#!/usr/bin/env python3
import argparse
import os
import sys
from tencentcloud.common import credential
from tencentcloud.apigateway.v20180808 import apigateway_client, models

###########################################################
# API Gateway Config
###########################################################

API_GATEWAY_REGION = os.environ["API_GATEWAY_REGION"]
API_GATEWAY_SERVICE_ID = os.environ["API_GATEWAY_SERVICE_ID"]
API_GATEWAY_API_ID = os.environ["API_GATEWAY_API_ID"]

###########################################################
# Setup Tencent Cloud Client
###########################################################
TENCENT_CLOUD_SECRET_ID = os.environ["TENCENT_CLOUD_SECRET_ID"]
TENCENT_CLOUD_SECRET_KEY = os.environ["TENCENT_CLOUD_SECRET_KEY"]

TENCENT_API_GATEWAY_CLIENT = apigateway_client.ApigatewayClient(
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
    parser = argparse.ArgumentParser(description="Deploy API Gateway")
    parser.add_argument("--type", type=str, required=True, choices=["COS"], help="The type of API Gateway backend")
    group_cos = parser.add_argument_group("COS")
    group_cos.add_argument("--bucket", type=str, help="The bucket of COS")
    group_cos.add_argument("--path", type=str, help="The path of COS files")
    args = parser.parse_args()

    # Read original API Gateway config.
    request = models.DescribeApiRequest()
    request.ServiceId = API_GATEWAY_SERVICE_ID
    request.ApiId = API_GATEWAY_API_ID
    api = TENCENT_API_GATEWAY_CLIENT.DescribeApi(request)
    print(f"[*] Original API Gateway Config: {api}")

    if args.type == "COS":
        update_cos_backend(api, args)
    else:
        print(f"[*] Unsupported backend type: {args.type}")
        sys.exit(1)
    
    # Release API Gateway update.
    request = models.ReleaseServiceRequest()
    request.ServiceId = API_GATEWAY_SERVICE_ID
    request.EnvironmentName = "release"
    request.ReleaseDesc = f"Update API {API_GATEWAY_API_ID} with arguments {args}."
    response = TENCENT_API_GATEWAY_CLIENT.ReleaseService(request)
    print(f"[*] Released API Gateway: {response}")