# CEW Training Platform - Operator Guide

This guide provides quick-start instructions for operating the CEW Training Platform.

## Table of Contents

1. [Getting Started](#getting-started)
2. [User Roles](#user-roles)
3. [Managing Scenarios](#managing-scenarios)
4. [Managing Labs](#managing-labs)
5. [Monitoring & Audit](#monitoring--audit)
6. [Emergency Procedures](#emergency-procedures)

## Getting Started

### Default Accounts

The platform includes three default accounts for testing:

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Administrator |
| instructor | instructor123 | Instructor |
| trainee | trainee123 | Trainee |

**⚠️ Change these passwords immediately in production!**

### First Login

1. Navigate to the platform URL (default: `http://localhost:3000`)
2. Enter credentials on the login page
3. You will be directed to the Dashboard (instructors/admins) or Scenarios page (trainees)

## User Roles

### Administrator
- Full system access
- User management (create, delete users)
- All instructor capabilities
- Access to audit logs

### Instructor
- Create and manage scenarios
- Activate/deactivate training labs
- Use emergency kill switch
- View audit logs
- Monitor active labs

### Trainee
- View scenarios
- Participate in activated labs
- Limited to read-only for most features

## Managing Scenarios

### Creating a Scenario

1. Go to **Scenarios** tab
2. Click **+ Create New Scenario** or **📋 Use Template**
3. Fill in scenario details:
   - Name and description
   - Network topology (nodes, networks)
   - Constraints (safety settings)
4. Click **Save**

### Using Templates

Templates provide pre-configured topologies:

- **Basic Lab Network**: Simple attacker/target setup
- **Enterprise Network**: Multi-segment corporate simulation
- **RF/EW Training**: SDR and wireless simulation

### Importing/Exporting

- Export scenarios as JSON or YAML for backup
- Import scenarios from files for sharing

## Managing Labs

### Activating a Scenario

1. Go to **Dashboard**
2. Find the scenario in the list
3. Click **Activate** to start the lab environment
4. Monitor status in **Instructor Controls**

### Lab Environment Details

Active labs show:
- Container count and status
- Network configuration
- Runtime duration
- Assigned resources

### Stopping Labs

**Individual Lab**: Click **Stop** next to the specific lab

**All Labs**: Use the **Emergency Kill Switch** (see Emergency Procedures)

## Monitoring & Audit

### Dashboard

The dashboard displays:
- **System Status**: Operational health
- **Scenarios**: Total and active count
- **Labs**: Active sessions and resources
- **Safety Status**: Air-gap, network, and RF constraints

### Audit Logs

Access via **Audit Logs** tab (Admin/Instructor only):

1. View all system activity
2. Filter by username or action type
3. Review timestamps and success/failure status

**Logged Actions**:
- Login/logout events
- Scenario operations
- Lab activations
- Kill switch usage
- User management

## Emergency Procedures

### Kill Switch

The **Emergency Kill Switch** immediately stops ALL active training scenarios and lab environments.

**Location**: Dashboard → Instructor Controls → 🛑 EMERGENCY KILL SWITCH

**When to Use**:
- Safety constraint violations
- Unauthorized activity detected
- System malfunction
- Exercise boundaries exceeded

**After Using Kill Switch**:
1. Review audit logs for the trigger
2. Investigate the incident
3. Document findings
4. Get approval before restarting exercises

### Safety Constraints

The platform enforces these constraints by default:

| Constraint | Default | Description |
|------------|---------|-------------|
| `allow_external_network` | `false` | Blocks internet/external access |
| `allow_real_rf` | `false` | Blocks real RF transmission |
| `isolated` networks | `true` | All lab networks are isolated |

**These constraints cannot be overridden** in the current prototype.

## Best Practices

### Before Each Exercise

1. Review the safety checklist (`docs/safety_checklist.md`)
2. Verify participant authorization
3. Confirm network isolation
4. Test the kill switch

### During Exercises

1. Monitor active labs regularly
2. Check audit logs for anomalies
3. Keep kill switch accessible
4. Document any issues immediately

### After Exercises

1. Deactivate all labs
2. Review audit logs
3. Document lessons learned
4. Update scenarios as needed

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Cannot login | Verify credentials, check if account is disabled |
| Lab won't start | Check scenario constraints, verify resources available |
| Kill switch not working | Refresh page, check backend health endpoint |
| Missing audit logs | Verify user has instructor/admin role |

### Health Check

Access the API health endpoint: `GET /health`

Expected response: `{"status": "healthy"}`

### Support

For additional support, refer to:
- `docs/architecture.md` - System architecture
- `docs/safety_checklist.md` - Safety requirements
- GitHub Issues - Bug reports and feature requests

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-28
