#!/usr/bin/env python3
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from qcloud_cos.cos_exception import CosClientError, CosServiceError


###########################################################
# COS Config
###########################################################

COS_REGION = os.environ["COS_REGION"]
COS_BUCKET = os.environ["COS_BUCKET"]
COS_UPLOAD_RETRY = 3

###########################################################
# Setup Tencent Cloud Client
###########################################################

TENCENT_CLOUD_SECRET_ID = os.environ["TENCENT_CLOUD_SECRET_ID"]
TENCENT_CLOUD_SECRET_KEY = os.environ["TENCENT_CLOUD_SECRET_KEY"]

COS_CLIENT = CosS3Client(CosConfig(
    Region=COS_REGION,
    SecretId=TENCENT_CLOUD_SECRET_ID,
    SecretKey=TENCENT_CLOUD_SECRET_KEY,
))


def check_file_exists(target: str) -> bool:
    try:
        COS_CLIENT.head_object(Bucket=COS_BUCKET, Key=target)
        return True
    except CosServiceError as e:
        if e.get_status_code() == 404 or e.get_error_code() == "NoSuchResource":
            return False
        print(f"[!] Failed to check file '{target}' in COS. Error: {e}")
        return False

def upload_file(source: str, target: str):
    print(f"[*] Uploading '{source}' to COS '{target}'......")
    for _ in range(COS_UPLOAD_RETRY):
        COS_CLIENT.upload_file(
            Bucket=COS_BUCKET,
            Key=target,
            LocalFilePath=source,
            EnableMD5=True,
        )

def upload_folder(source: str, target: str):
    executor = ThreadPoolExecutor()
    for path, _, file_list in os.walk(source):
        for file_name in file_list:
            source_file = os.path.join(path, file_name)
            target_file = os.path.join(target, os.path.relpath(source_file, source))
            exists = check_file_exists(target_file)
            if not exists:
                executor.submit(upload_file, source_file, target_file)
    executor.shutdown(wait=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Upload file/folder to COS.")
    parser.add_argument("source", help="The local path of file/folder to upload.", type=str)
    parser.add_argument("target", help="The target path in COS bucket.", type=str)
    args = parser.parse_args()

    if os.path.isfile(args.source):
        upload_file(args.source, args.target)
    elif os.path.isdir(args.source):
        upload_folder(args.source, args.target)
    else:
        print(f"[!] Source path '{args.source}' is not a file or folder.")
        sys.exit(1)