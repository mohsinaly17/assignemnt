# restart-project.ps1
# Usage: run this script from the project root: .\restart-project.ps1
# Requires: AWS CLI configured, Docker Desktop running, SSH key already authorized on the server.

$InstanceId = "i-0c1c703fffd2be2f0"

Write-Host "Starting EC2 instance..." -ForegroundColor Cyan
aws ec2 start-instances --instance-ids $InstanceId | Out-Null

Write-Host "Waiting for instance to reach running state..." -ForegroundColor Cyan
aws ec2 wait instance-running --instance-ids $InstanceId

$IP = aws ec2 describe-instances --instance-ids $InstanceId --query "Reservations[].Instances[].PublicIpAddress" --output text
Write-Host "Instance is running at: $IP" -ForegroundColor Green

$inventoryPath = "ansible\inventory.ini"
$inventoryContent = "[app_servers]`napp_server ansible_host=$IP ansible_user=ubuntu ansible_ssh_private_key_file=/root/.ssh/id_rsa ansible_ssh_common_args=`"-o StrictHostKeyChecking=no`""
Set-Content -Path $inventoryPath -Value $inventoryContent
Write-Host "Ansible inventory updated." -ForegroundColor Green

Write-Host "Waiting 15 seconds for SSH to become ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

Write-Host "Running Ansible to confirm Docker and the app container are healthy..." -ForegroundColor Cyan
docker run --rm -v ${PWD}:/project -v $HOME\.ssh:/root/.ssh-host --workdir /project/ansible willhallonline/ansible:latest sh -c "mkdir -p /root/.ssh && cp /root/.ssh-host/id_rsa /root/.ssh/id_rsa && chmod 600 /root/.ssh/id_rsa && ansible-playbook -i inventory.ini playbook.yml"

Write-Host "Checking the live app..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://$IP" -UseBasicParsing
    Write-Host "App is live:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 5
} catch {
    Write-Host "App did not respond yet. It may need a few more seconds. Try: irm http://$IP" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done. Server IP: $IP" -ForegroundColor Green
Write-Host "If this IP differs from what is saved in your GitHub secret EC2_HOST, update it in your repo settings." -ForegroundColor Yellow
