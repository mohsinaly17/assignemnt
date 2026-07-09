from flask import Flask, jsonify
from datetime import datetime, timezone
import socket
import time
import os
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


def get_aws_metadata():
    """Queries the EC2 Instance Metadata Service (IMDSv2) for real, live
    facts about the AWS infrastructure Terraform provisioned. Returns a
    dict with a status flag, since this only works when actually running
    on an EC2 instance (fails gracefully everywhere else, e.g. local dev)."""
    try:
        token_req = urllib.request.Request(
            f"{IMDS_BASE}/api/token",
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
        )
        token = urllib.request.urlopen(token_req, timeout=1).read().decode()

        def fetch(path):
            req = urllib.request.Request(
                f"{IMDS_BASE}/meta-data/{path}",
                headers={"X-aws-ec2-metadata-token": token},
            )
            return urllib.request.urlopen(req, timeout=1).read().decode()

        return {
            "status": "reachable",
            "instance_id": fetch("instance-id"),
            "instance_type": fetch("instance-type"),
            "availability_zone": fetch("placement/availability-zone"),
            "public_ipv4": fetch("public-ipv4"),
        }
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"status": "unreachable (not running on EC2, or IMDS blocked)"}


def get_deployment_info():
    """Reads the timestamp Ansible actually wrote to disk during its most
    recent playbook run. If this file is missing, Ansible has never
    successfully deployed to this container."""
    marker_path = "/deploy_info/.deployed_at"
    if os.path.exists(marker_path):
        with open(marker_path) as f:
            deployed_at = f.read().strip()
        return {"status": "confirmed", "last_deployed_at_utc": deployed_at}
    return {"status": "no deployment marker found"}


def get_docker_info():
    """Confirms this process is genuinely running inside a Docker
    container by checking for the /.dockerenv marker file Docker itself
    creates, rather than just assuming it."""
    if os.path.exists("/.dockerenv"):
        return {"status": "confirmed", "note": "process is running inside a Docker container"}
    return {"status": "not running inside Docker"}


@app.route("/")
def home():
    return jsonify({
        "message": "Hello from the automated Docker deployment!",
        "hostname": socket.gethostname(),
        "server_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "app_uptime": format_uptime(time.time() - START_TIME),
        "checks": {
            "flask_application": {"status": "running"},
            "docker": get_docker_info(),
            "ansible_deployment": get_deployment_info(),
            "aws_ec2_instance": get_aws_metadata(),
        }
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
