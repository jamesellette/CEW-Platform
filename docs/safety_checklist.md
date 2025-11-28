# CEW Training Platform - Safety Checklist

This document provides a comprehensive safety checklist for operating the CEW Training Platform. **All users must review and acknowledge these guidelines before using the platform.**

## ⚠️ Critical Safety Requirements

### 1. Network Isolation (Air-Gap)

- [ ] **NEVER connect training environments to operational networks**
- [ ] Verify all lab environments are isolated from production systems
- [ ] Ensure no external network egress is configured for lab containers
- [ ] Use only designated training network segments
- [ ] The platform enforces `allow_external_network: false` by default

### 2. RF/Wireless Safety

- [ ] **NEVER transmit on real RF frequencies during training**
- [ ] Use only simulated RF environments (GNU Radio simulation mode)
- [ ] Verify SDR hardware is disconnected or in receive-only mode
- [ ] The platform enforces `allow_real_rf: false` by default
- [ ] All wireless training must use isolated, shielded environments

### 3. Target Assets

- [ ] Use ONLY synthetic/simulated target assets
- [ ] Never target real systems, networks, or infrastructure
- [ ] Verify all IP addresses are within designated training ranges
- [ ] Document all synthetic assets before exercises

## 🔐 Access Control Checklist

### User Management

- [ ] All users have appropriate role assignments (Admin/Instructor/Trainee)
- [ ] Default passwords have been changed
- [ ] Inactive accounts are disabled
- [ ] User access is reviewed periodically

### Session Security

- [ ] JWT tokens expire appropriately (default: 60 minutes)
- [ ] Users log out after training sessions
- [ ] Shared workstations are secured between users

## 📋 Pre-Exercise Checklist

Before starting any training exercise:

1. [ ] Verify network isolation is active
2. [ ] Confirm all participants are authorized
3. [ ] Review scenario constraints (no external network, no real RF)
4. [ ] Ensure kill switch is functional and accessible
5. [ ] Document exercise scope and boundaries
6. [ ] Brief all participants on safety protocols
7. [ ] Verify audit logging is enabled

## 🛑 Emergency Procedures

### Kill Switch Usage

The **Emergency Kill Switch** immediately stops ALL active training scenarios and lab environments. Use when:

- Unauthorized network activity is detected
- Safety constraints are violated
- Equipment malfunction occurs
- Exercise boundaries are exceeded

**Location**: Dashboard → Instructor Controls → Emergency Kill Switch

### Incident Response

1. Activate kill switch immediately
2. Document the incident in audit logs
3. Notify platform administrator
4. Do not restart exercises until root cause is identified
5. Update safety procedures as needed

## 📊 Audit & Compliance

### Required Logging

The platform automatically logs:
- All login attempts (successful and failed)
- Scenario activations and deactivations
- Kill switch usage
- User management actions
- System status changes

### Review Schedule

- [ ] Daily: Review active sessions and unusual activity
- [ ] Weekly: Audit log review for compliance
- [ ] Monthly: User access review and cleanup
- [ ] Quarterly: Full security assessment

## 🏗️ Infrastructure Requirements

### Minimum Isolation Requirements

1. **Physical Isolation**: Training systems on separate network segments
2. **Logical Isolation**: VLANs or network namespaces for lab environments
3. **Container Isolation**: Docker networks with no external connectivity
4. **Data Isolation**: Training data stored separately from production

### Monitoring

- [ ] Network traffic monitoring enabled
- [ ] Container resource limits configured
- [ ] Disk space alerts configured
- [ ] System health checks running

## ✅ Acknowledgment

By using this platform, you acknowledge that:

1. This platform is for **TRAINING PURPOSES ONLY**
2. You will **NOT** connect to operational networks
3. You will **NOT** target real systems or infrastructure
4. You will follow all safety protocols and use the kill switch when necessary
5. You will report any safety concerns immediately

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-28  
**Review Required**: Quarterly
