# Automated Docker Deployment — Terraform + Ansible + GitHub Actions

This project automates the end-to-end deployment of a containerized sample
web application onto AWS, using **three integrated automation tools**:

| Stage | Tool | Purpose |
|---|---|---|
| Infrastructure provisioning | **Terraform** | Creates the EC2 instance, security group, and networking |
| Configuration management | **Ansible** | Installs Docker on the server, ships the app, builds and runs the container |
| CI/CD | **GitHub Actions** | Automatically re-deploys the app whenever code is pushed to `main` |

## Architecture

```
Developer --push--> GitHub repo --triggers--> GitHub Actions
                                                    |
                                          (SSH via secrets)
                                                    v
                                          Ansible playbook run
                                                    |
                              installs Docker, builds image, runs container
                                                    v
                                     EC2 instance (provisioned by Terraform)
                                                    |
                                         Docker container serving Flask app
                                                    v
                                        http://<EC2-public-ip>  (port 80)
```

## Folder structure

```
project/
├── terraform/          # Infrastructure as Code (EC2, security group)
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── ansible/             # Configuration management + deployment
│   ├── playbook.yml
│   ├── requirements.yml
│   ├── ansible.cfg
│   └── inventory.ini.example
├── app/                 # Sample Flask application
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
└── .github/workflows/
    └── deploy.yml       # CI/CD pipeline
```

## One-time setup

1. **Generate an SSH key pair** (if you don't already have one):
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
   ```

2. **Configure AWS credentials** locally:
   ```bash
   aws configure
   ```

## Step 1 — Provision infrastructure with Terraform

```bash
cd terraform
terraform init
terraform apply -var="key_name=my-deploy-key"
```

Note the `instance_public_ip` output — you'll need it for the next step.

## Step 2 — Configure the server and deploy with Ansible

```bash
cd ../ansible
cp inventory.ini.example inventory.ini
# edit inventory.ini and replace REPLACE_WITH_EC2_PUBLIC_IP with the Terraform output
ansible-galaxy collection install -r requirements.yml
ansible-playbook playbook.yml
```

Visit `http://<EC2-public-ip>` in your browser — you should see the JSON
response from the Flask app.

## Step 3 — Set up CI/CD (GitHub Actions)

In your GitHub repository, go to **Settings → Secrets and variables → Actions**
and add:

| Secret name | Value |
|---|---|
| `EC2_HOST` | The EC2 public IP from Terraform's output |
| `EC2_SSH_PRIVATE_KEY` | Contents of your `~/.ssh/id_rsa` private key |

From now on, every push to `main` automatically re-runs the Ansible
playbook against the server, rebuilding and restarting the container with
the latest code — no manual redeployment needed.

## Tearing down

To avoid AWS charges after you're done:

```bash
cd terraform
terraform destroy
```

## Automation flow summary

1. Terraform provisions a clean Ubuntu EC2 instance and opens the necessary
   ports (22, 80, 5000).
2. Ansible connects over SSH, installs Docker, copies the application
   source, builds the Docker image, and runs it as a container with a
   restart policy so it survives reboots.
3. GitHub Actions ties it together: any code push triggers the pipeline,
   which re-runs the Ansible playbook so the live server always reflects
   the latest commit.
