# EV Charging Slot Booking System
## Step 13–14: Configuration Management, Provisioning and Reliability

### Step 13 — Configuration Management

**Tool:** Ansible
**Control node:** Ubuntu on WSL2
**Managed target:** Isolated Ubuntu 24.04 SSH container

The Ansible configuration playbook manages:
- Required operating-system packages
- Dedicated deployment user: evdeploy
- Application directories under /opt/ev-charging
- Deployment configuration template

Validation:
- SSH connectivity: PASS
- Configuration playbook: PASS
- Deployment user and directories: PASS
- Second execution: changed=0, failed=0

The second playbook run confirmed idempotency for the managed configuration.

### Step 14 — Automated Deployment and Reliability

The deployment was orchestrated through Ansible and Docker Compose
using an isolated Compose project.

- Compose project: evcharging_ansible_lab
- Application endpoint: http://127.0.0.1:8090/health/
- Dedicated network: evcharging_ansible_lab_net
- Dedicated PostgreSQL volume: evcharging_ansible_lab_postgres_data

The deployment used versioned images for release:
1.0.0-build11-496074a

Health validation returned:
{"status":"healthy","database":"connected"}

### Rollback and Recovery Test

The isolated deployment was switched to:
1.0.0-build1-19e4663

The previous release passed its application and database health checks.
The deployment was then restored to:
1.0.0-build11-496074a

Post-recovery validation confirmed:
- Application status: healthy
- Database status: connected
- Final image tag: 1.0.0-build11-496074a
- Rollback playbook failures: 0

### Isolation and Safety

The lab uses a separate Compose project, network, database volume,
and host port. The existing deployments on ports 8081 and 8088 were
not used as the Step 14 test environment.

### Evidence

Execution output is stored in the local Ansible lab evidence directory.
See the captured idempotency, deployment, rollback, health, version,
and container-status files.

### Scope and Limitations

The managed Ansible target is an Ubuntu container, not a full virtual
machine. Docker Compose deployment is orchestrated on the WSL2 control
node using Docker Desktop. This validates configuration management,
deployment, health checks, version switching, and recovery in an
isolated lab, but is not a full production VM provisioning exercise.
