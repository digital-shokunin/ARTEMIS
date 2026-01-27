# GCP Specialist Design Document

**Date:** 2026-01-27
**Author:** Claude Sonnet 4.5
**Status:** Completed

## Overview

Created a comprehensive GCP (Google Cloud Platform) security specialist instruction file for the ARTEMIS Codex agent. This file provides detailed techniques, tools, and commands for penetration testing GCP environments across the full attack lifecycle.

## Design Decisions

### 1. Attack Phase Organization

Organized the specialist file into six chronological attack phases:

1. **Initial Access & Reconnaissance** - External enumeration and initial foothold
2. **Enumeration with Credentials** - Deep reconnaissance with authenticated access
3. **Privilege Escalation** - Elevation of permissions and access
4. **Lateral Movement** - Moving across projects, VMs, and services
5. **Persistence** - Maintaining access through backdoors
6. **Data Exfiltration & Impact** - Data extraction and covering tracks

**Rationale:** This mirrors a real penetration testing engagement flow, making it intuitive for the agent to follow progressive stages.

### 2. Context-Aware Access Level Indicators

Each technique is tagged with its required access level:
- 🌐 **EXTERNAL/UNAUTHENTICATED** - No credentials needed
- 🔑 **CREDENTIALS REQUIRED** - Need service account key or OAuth token
- 💻 **VM/CONTAINER ACCESS** - Must execute from within GCP compute resource
- 🎯 **PRIVILEGED ACCESS** - Need elevated IAM permissions
- 🏢 **ORGANIZATION ACCESS** - Requires org-level permissions

**Rationale:** Helps the agent understand what's possible from its current position and prevents attempting techniques that require access it doesn't have (e.g., trying to access metadata service from external position).

### 3. Tool-First Approach

Each phase leads with automated tools (prowler, ScoutSuite, gcp-iam-collector) followed by manual techniques.

**Rationale:** Provides quick reconnaissance wins with automated tools, then deeper exploitation through manual commands. Maximizes efficiency while maintaining thoroughness.

### 4. Production Environment Focus

Emphasized coverage of commonly deployed GCP services:
- Compute Engine (VMs, disks, snapshots)
- Cloud Storage (buckets, objects)
- IAM (service accounts, roles, permissions)
- GKE (Kubernetes clusters)
- Cloud Functions & Cloud Run
- Cloud SQL & BigQuery
- Secrets Manager

**Rationale:** Focuses on services most likely to be encountered in real production environments, making the specialist immediately practical.

## Key Features

### Comprehensive Coverage (73 Techniques)

- 9 reconnaissance techniques
- 16 enumeration techniques
- 9 privilege escalation techniques
- 12 lateral movement techniques
- 12 persistence techniques
- 15 exfiltration & impact techniques

### Metadata Service Exploitation

Special emphasis on GCP metadata service (169.254.169.254) exploitation, clearly marking it as requiring VM/container access. Includes:
- Service account token extraction
- Scope enumeration
- SSH key discovery
- Project information gathering

### IAM Privilege Escalation Paths

Detailed coverage of common IAM-based privilege escalation:
- Service account impersonation
- IAM policy modification
- Service account key creation
- Custom role exploitation
- actAs permission abuse

### Cross-Service Lateral Movement

Techniques for pivoting between GCP services:
- Cloud Function → Storage
- Cloud Run → Compute Engine
- GKE pod → Node → Cluster
- Cross-project access
- Shared VPC pivoting

### Practical Command Examples

Every technique includes:
- Exact command syntax with proper flags
- Explanation of what the command does
- Common variations and use cases
- Error handling considerations

## Reference Integration

Incorporated techniques from authoritative sources:
- **HackTricks GCP Wiki** - Privilege escalation paths, metadata exploitation
- **Six2dez Pentest Book** - Enumeration workflows, tool usage
- **Prowler** - Automated security assessment capabilities
- **Google Cloud SDK** - Official gcloud command patterns

## Tools Included

### Automated Assessment
- Prowler (comprehensive security audit)
- ScoutSuite (configuration review)
- gcp-iam-collector (IAM mapping)

### Enumeration
- GCPBucketBrute (bucket discovery)
- gcloud CLI (primary tool)
- gsutil (storage operations)
- kubectl (Kubernetes)
- bq (BigQuery)

### Exploitation
- Metadata service (curl-based)
- IAM manipulation (gcloud iam)
- Container tools (docker, dive)
- Custom scripts (bash, python)

## Security Considerations

This specialist file contains intentional exploitation techniques and insecure code examples for security testing purposes. It is designed for:
- Authorized penetration testing only
- Research and education
- Red team operations on sanctioned targets
- Defensive security improvement

The file should only be used against environments where explicit written authorization has been obtained.

## File Location

`/home/digish0/ARTEMIS/codex-rs/core/gcp.md`

## File Statistics

- **Total Lines:** 1,652
- **Techniques:** 73
- **Tools Covered:** 15+
- **GCP Services:** 12+
- **Attack Phases:** 6

## Usage Pattern

The agent will use this specialist when:
1. User requests GCP security assessment
2. Target environment is identified as GCP
3. Cloud penetration testing is the objective
4. GCP-specific exploitation is needed

The agent should follow the phases sequentially, starting with reconnaissance and progressing through the attack lifecycle as access is gained.

## Future Enhancements

Potential additions for future versions:
- Workspace/Identity exploitation techniques
- Cloud Armor bypass methods
- Apigee API gateway testing
- Firebase security assessment
- More GKE-specific container escapes
- Organization-level attack chains
- Multi-cloud pivot scenarios (GCP → AWS/Azure)
