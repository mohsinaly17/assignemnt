from flask import Flask, jsonify
from datetime import datetime, timezone
import socket
import time
import os
import json
import urllib.request
import urllib.error

app = Flask(__name__)

START_TIME = time.time()
IMDS_BASE = "http://169.254.169.254/latest"


def format_uptime(seconds):
    seconds = int(seconds)
    hrs, rem = divmod(seconds, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0:
        return f"{hrs}h {mins}m {secs}s"
    elif mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def imds_fetch(path, token):
    req = urllib.request.Request(
        f"{IMDS_BASE}/meta-data/{path}",
        headers={"X-aws-ec2-metadata-token": token},
    )
    return urllib.request.urlopen(req, timeout=1).read().decode()


def get_aws_and_terraform_info():
    """Queries the real EC2 Instance Metadata Service. Everything returned
    here is infrastructure Terraform actually provisioned -- this is not
    hardcoded, it is read live from the instance itself."""
    try:
        token_req = urllib.request.Request(
            f"{IMDS_BASE}/api/token",
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
        )
        token = urllib.request.urlopen(token_req, timeout=1).read().decode()

        security_groups = imds_fetch("security-groups", token).split("\n")

        return {
            "status": "reachable",
            "provisioned_by": "Terraform (main.tf)",
            "instance_id": imds_fetch("instance-id", token),
            "instance_type": imds_fetch("instance-type", token),
            "ami_id": imds_fetch("ami-id", token),
            "availability_zone": imds_fetch("placement/availability-zone", token),
            "public_ipv4": imds_fetch("public-ipv4", token),
            "private_ipv4": imds_fetch("local-ipv4", token),
            "security_groups": security_groups,
        }
    except (urllib.error.URLError, TimeoutError, OSError):
        return {
            "status": "unreachable",
            "note": "Instance metadata service did not respond. On Docker, this usually means the metadata hop limit needs increasing (aws ec2 modify-instance-metadata-options --http-put-response-hop-limit 2), or this is not running on EC2 at all.",
        }


def get_ansible_deployment_info():
    """Reads a marker file that Ansible itself writes to disk during every
    playbook run, containing the real deployment timestamp and, when
    deployed via CI/CD, the exact git commit and workflow run number."""
    marker_path = "/deploy_info/.deployed_at"
    if not os.path.exists(marker_path):
        return {"status": "no deployment marker found -- Ansible has not deployed to this container"}
    try:
        with open(marker_path) as f:
            data = json.load(f)
        return {"status": "confirmed", **data}
    except (json.JSONDecodeError, ValueError):
        with open(marker_path) as f:
            legacy_timestamp = f.read().strip()
        return {"status": "confirmed", "deployed_at_utc": legacy_timestamp, "note": "legacy marker format"}


def get_docker_info():
    """Confirms this process is genuinely running inside a Docker container
    by checking for /.dockerenv, a file Docker itself creates."""
    if os.path.exists("/.dockerenv"):
        return {
            "status": "confirmed",
            "note": "process is running inside a Docker container built from app/Dockerfile",
            "base_image": "python:3.12-slim",
        }
    return {"status": "not running inside Docker"}


def get_cicd_info(ansible_info):
    """Surfaces CI/CD traceability using the same data Ansible wrote,
    so you can see whether the live app was deployed manually or by
    GitHub Actions, and exactly which commit is running."""
    if ansible_info.get("status") != "confirmed":
        return {"status": "unknown -- no deployment record found"}
    return {
        "status": "confirmed",
        "deployed_by": ansible_info.get("deployed_by", "unknown"),
        "git_commit": ansible_info.get("git_commit", "unknown"),
        "github_actions_run_number": ansible_info.get("run_number", "n/a"),
        "workflow_file": ".github/workflows/deploy.yml",
    }


@app.route("/")
def home():
    ansible_info = get_ansible_deployment_info()
    return jsonify({
        "message": "we changed the line !!!!!!!!!!!!!!!!!!!!!!!!!!!",
        "hostname": socket.gethostname(),
        "server_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "app_uptime": format_uptime(time.time() - START_TIME),
        "checks": {
            "flask_application": {"status": "running"},
            "docker": get_docker_info(),
            "ansible_deployment": ansible_info,
            "terraform_and_aws_infrastructure": get_aws_and_terraform_info(),
            "cicd_pipeline": get_cicd_info(ansible_info),
        }
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
