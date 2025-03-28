# -*- coding: utf8 -*-
import base64
import io
import json
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


def search_latest_certificate(domain: str) -> str:
    req = models.DescribeCertificatesRequest()
    req.SearchKey = domain
    req.ExpirationSort = "DESC"
    req.FilterSource = "upload"
    resp = TENCENT_SSL_CLIENT.DescribeCertificates(req)
    return resp.Certificates[0].CertificateId

def download_certificate(domain: str, certificateID: str) -> bytes:
    req = models.DownloadCertificateRequest()
    req.CertificateId = certificateID
    resp = TENCENT_SSL_CLIENT.DownloadCertificate(req)

    zipContent = base64.b64decode(resp.Content)
    with zipfile.ZipFile(io.BytesIO(zipContent)) as zipFile:
        zipFile.extractall("/tmp")
        return zipFile.read(f"{domain}.pem")

def upload_certificate(keyPath: str, certificatePath: str):
    req = models.UploadCertificateRequest()

    with open(keyPath, "r") as f:
        req.CertificatePrivateKey = f.read()
    with open(certificatePath, "r") as f:
        req.CertificatePublicKey = f.read()

    resp = TENCENT_SSL_CLIENT.UploadCertificate(req)
    print(f"[*] Uploaded certificate. Response: {resp}")

def update_certificate(certificateID: str, types: list[str], types_regions: dict[str, list[str]], keyPath: str, certificatePath: str):
    req = models.UpdateCertificateInstanceRequest()
    req.OldCertificateId = certificateID

    req.ResourceTypes = types
    req.ResourceTypesRegions = list()
    for type, regions in types_regions.items():
        region = models.ResourceTypeRegions()
        region.ResourceType = type
        region.Regions = regions
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

def handle_domain(domain: str, domain_config: dict):
    types = domain_config.get("types", [])
    types_regions = domain_config.get("types_regions", [])

    # Search latest certificate.
    certificateID = search_latest_certificate(domain)
    print(f"[*] Latest certificate ID: {certificateID}")

    # Download online certificate.
    onlineCert = download_certificate(domain, certificateID)
    print(f"[*] Online certificate: {onlineCert}")

    # Check if the certificate is renewed.
    with open(f"{CONFIG_HOME}/{domain}_ecc/fullchain.cer", "rb") as f:
        localCert = f.read()
        print(f"[*] Local certificate: {localCert}")

        if onlineCert == localCert:
            print("[*] Certificate is not renewed.")
            return "Not Renewed"

    # Update renewed certificate.
    update_certificate(certificateID, types, types_regions,
        f"{CONFIG_HOME}/{domain}_ecc/{domain}.key",
        f"{CONFIG_HOME}/{domain}_ecc/fullchain.cer",
    )

    return "Done"

def main_handler(event, context):
    params = json.loads(event["Message"])

    # Renew all the certificates.
    os.system(f"{HOME}/acme.sh --cron --home {HOME} --config-home {CONFIG_HOME}")

    # Check each domain.
    for domain, domain_config in params.items():
        print(f"[*] Handling domain: {domain}")
        result = handle_domain(domain, domain_config)
        print(f"[*] Result: {result}")