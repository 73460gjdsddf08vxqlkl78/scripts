# -*- coding: utf8 -*-
import base64
import io
import os
import zipfile
from tencentcloud.common import credential
from tencentcloud.ssl.v20191205 import ssl_client, models

###########################################################
# acme.sh Config
###########################################################

HOME = "/opt/acme.sh"
CONFIG_HOME = "/mnt/etc/acme.sh"

###########################################################
# SSL Certificate Config
###########################################################

DOMAIN = os.environ["DOMAIN"]
CERTIFICATE_RESOURCE_TYPES = os.environ.get("CERTIFICATE_RESOURCE_TYPES", "apigateway").split(",")
CERTIFICATE_RESOURCE_TYPES_REGIONS = os.environ.get("CERTIFICATE_RESOURCE_TYPES_REGIONS", "ap-hongkong").split(",")

###########################################################
# Setup Tencent Cloud Client
###########################################################
TENCENT_CLOUD_SECRET_ID = os.environ["TENCENT_CLOUD_SECRET_ID"]
TENCENT_CLOUD_SECRET_KEY = os.environ["TENCENT_CLOUD_SECRET_KEY"]

TENCENT_SSL_CLIENT = ssl_client.SslClient(
    credential.Credential(
        TENCENT_CLOUD_SECRET_ID,
        TENCENT_CLOUD_SECRET_KEY,
    ),
    None,
)


def search_latest_certificate() -> str:
    req = models.DescribeCertificatesRequest()
    req.SearchKey = DOMAIN
    req.ExpirationSort = "DESC"
    req.FilterSource = "upload"
    resp = TENCENT_SSL_CLIENT.DescribeCertificates(req)
    return resp.Certificates[0].CertificateId

def download_certificate(certificateID: str) -> bytes:
    req = models.DownloadCertificateRequest()
    req.CertificateId = certificateID
    resp = TENCENT_SSL_CLIENT.DownloadCertificate(req)

    zipContent = base64.b64decode(resp.Content)
    with zipfile.ZipFile(io.BytesIO(zipContent)) as zipFile:
        zipFile.extractall("/tmp")
        return zipFile.read(f"{DOMAIN}.pem")

def upload_certificate(keyPath: str, certificatePath: str):
    req = models.UploadCertificateRequest()

    with open(keyPath, "r") as f:
        req.CertificatePrivateKey = f.read()
    with open(certificatePath, "r") as f:
        req.CertificatePublicKey = f.read()

    resp = TENCENT_SSL_CLIENT.UploadCertificate(req)
    print(f"[*] Uploaded certificate. Response: {resp}")

def update_certificate(certificateID: str, keyPath: str, certificatePath: str):
    req = models.UpdateCertificateInstanceRequest()
    req.OldCertificateId = certificateID

    req.ResourceTypes = CERTIFICATE_RESOURCE_TYPES
    req.ResourceTypesRegions = list()
    for t in CERTIFICATE_RESOURCE_TYPES:
        region = models.ResourceTypeRegions()
        region.ResourceType = t
        region.Regions = CERTIFICATE_RESOURCE_TYPES_REGIONS
        req.ResourceTypesRegions.append(region)

    with open(keyPath, "r") as f:
        req.CertificatePrivateKey = f.read()
    with open(certificatePath, "r") as f:
        req.CertificatePublicKey = f.read()

    req.ExpiringNotificationSwitch = 1
    req.Repeatable = False
    req.AllowDownload = True

    resp = TENCENT_SSL_CLIENT.UpdateCertificateInstance(req)
    print(f"[*] Updated certificate {certificateID}. Response: {resp}")

def main_handler(event, context):
    # Renew certificate.
    os.system(f"{HOME}/acme.sh --cron --home {HOME} --config-home {CONFIG_HOME}")

    # Search latest certificate.
    certificateID = search_latest_certificate()
    print(f"[*] Latest certificate ID: {certificateID}")

    # Download online certificate.
    onlineCert = download_certificate(certificateID)
    print(f"[*] Online certificate: {onlineCert}")

    # Check if the certificate is renewed.
    with open(f"{CONFIG_HOME}/{DOMAIN}_ecc/fullchain.cer", "rb") as f:
        localCert = f.read()
        print(f"[*] Local certificate: {localCert}")

        if onlineCert == localCert:
            print("[*] Certificate is not renewed.")
            return "Not Renewed"

    # Update renewed certificate.
    update_certificate(certificateID, 
        f"{CONFIG_HOME}/{DOMAIN}_ecc/{DOMAIN}.key", 
        f"{CONFIG_HOME}/{DOMAIN}_ecc/fullchain.cer",
    )

    return "Done"

if __name__ == "__main__":
    main_handler(None, None)