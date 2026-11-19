# Security & Encryption Architecture Specification

> **End-to-End Cryptographic Security, Data Protection at Rest, In-Transit Encryption, Key Management, and Compliance Standards**

---

## 1. Executive Summary & Security Philosophy

The system implements a defense-in-depth security model to ensure full confidentiality, data integrity, and compliance across every layer of the containerized architecture. 

Data is protected across all three fundamental states:
1. **Data-in-Transit (Network)**: Encrypted communication between users, microservices, databases, and workflow orchestration engines.
2. **Data-at-Rest (Storage)**: Cryptographic protection for persistent volumes, databases, Redis caches, and environment secrets.
3. **Data-in-Use (Memory)**: Secure key handling, non-root process isolation, and ephemeral memory management.

```
       [ Client Browser ]
               │
          HTTPS / TLS 1.3
               │
               ▼
     ┌───────────────────┐
     │  API Gateway / UI │
     └───────────────────┘
               │
     mTLS / gRPC Encrypted
     (finverify_finverify-net)
               │
     ┌─────────┴─────────┐
     │                   │
     ▼                   ▼
┌─────────┐        ┌──────────────┐          AES-256 Cryptographic Volume
│ Workers │        │ Temporal Engine │ ───▶ [ Data at Rest: PG & Redis ]
└─────────┘        └──────────────┘          (finverify_pg_data, redis_data)
```

---

## 2. Encryption in Transit (Data-in-Motion)

All network traffic—both external user requests and internal container-to-container communication—is strictly encrypted using industry-standard protocols.

### 1. External Traffic (Client $\leftrightarrow$ API Gateway & Frontend)
- **Protocol**: TLS 1.3 / HTTPS (Fallback to TLS 1.2 minimum).
- **Cipher Suites**: High-strength modern ciphers only (`TLS_AES_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256`).
- **Certificates**: X.509 certificates issued via automated ACME (Let's Encrypt) or internal PKI.
- **HSTS Policy**: Strict Transport Security (`max-age=31536000; includeSubDomains; preload`).

### 2. Internal Microservice Communication (Container $\leftrightarrow$ Container)
- **Isolated Docker Network**: Services communicate across a private, non-routable virtual network (`finverify_finverify-net`).
- **mTLS (Mutual TLS)**: Inter-service communication between API services (`finverify-api`), background worker nodes (`finverify-worker`), and Temporal workflow orchestrators (`finverify-temporal`) uses mTLS with client certificate verification.
- **gRPC Transport Encryption**: Temporal engine gRPC payload channels are secured via TLS with custom DataConverter payload encryption.

---

## 3. Encryption at Rest (Data-at-Rest)

Data persisted to disk—including databases, cache snapshots, and workflow execution states—is protected using strong symmetric encryption algorithms.

### 1. Database Volume Encryption (`finverify_pg_data`)
- **Block-Level Encryption**: Host-level persistent storage volumes (`finverify_pg_data`) are encrypted using **AES-256-XTS** (LUKS / AWS KMS / Cloud Disk Encryption).
- **Application Column-Level Encryption**: Sensitive database fields (API keys, PII, authentication tokens) are encrypted at the application layer using **AES-256-GCM** before executing `INSERT` / `UPDATE` SQL queries.
  - *Initialization Vector (IV)*: Random 96-bit IV generated per row to prevent pattern recognition.
  - *Authentication Tag*: 128-bit GCM authentication tag verifies payload integrity.

### 2. Redis Cache & Queue Encryption (`finverify_redis_data`)
- **Transport Security**: Redis 7 `redis:7-alpine` configured with TLS support for client connections.
- **Persistence Encryption**: In-memory Redis RDB snapshots and Append-Only Files (AOF) stored on `finverify_redis_data` volume are encrypted at rest using AES-256.

### 3. Password & Credential Hashing
- **Algorithm**: **Argon2id** (Key derivation function) or **Bcrypt** (cost factor $\ge 12$).
- **Salting**: Cryptographically secure unique 16-byte salt per password, preventing rainbow table attacks.

---

## 4. Cryptographic Key Management & Secrets Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    KMS / Secret Provider                        │
│             (AWS KMS / HashiCorp Vault / Docker Secrets)         │
└─────────────────────────────────────────────────────────────────┘
                                │
                    Master Encryption Key (MEK)
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│               Application Key Rotation Manager                   │
│          Generates Data Encryption Keys (DEKs) per Tenant        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Protection Rules
1. **Separation of Duties**: Master Encryption Keys (MEK) are stored in secure Key Management Systems (KMS) or hardware security modules (HSM) and are never exposed in source code.
2. **Environment Variable Security**: Sensitive API keys (`ANTHROPIC_API_KEY`, DB passwords) are injected into containers at runtime via `.env` / Docker secret mounts and never baked into Docker image layers.
3. **Key Rotation Policy**:
   - Data Encryption Keys (DEKs) rotate automatically every 90 days.
   - Re-encryption routines support seamless rotation without downtime.

---

## 5. Summary Matrix of Encryption Standards

| Protection Domain | Target Component / Resource | Encryption Standard / Protocol | Key Size / Parameter |
| :--- | :--- | :--- | :--- |
| **Network (External)** | Web Frontend & API Gateway | TLS 1.3 / HTTPS | 2048/4096-bit RSA or ECDSA P-256 |
| **Network (Internal)** | Container Inter-Communication | mTLS & gRPC TLS | X.509 Mutual Auth |
| **Database Storage** | PostgreSQL Volume (`finverify_pg_data`) | AES-256-XTS | 256-bit Key |
| **Sensitive Fields** | DB Column Encryption (PII/Tokens) | AES-256-GCM | 256-bit Key + 96-bit IV |
| **Cache Storage** | Redis Volume (`finverify_redis_data`) | TLS 1.3 + AES-256 Volume | 256-bit Key |
| **User Passwords** | User Authentication Credentials | Argon2id / Bcrypt | Cost = 12, Salt = 16-byte |
| **Secrets Management**| Environment Variables & API Keys | Docker Secrets / KMS | Envelope Encryption |

---

## Related Documentation Files

- [PROJECT_OVERVIEW.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/PROJECT_OVERVIEW.md) — Architectural overview and system components.
- [DOCKER.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/DOCKER.md) — Containerization architecture, volume mounts, and security isolation.
- [SQL_DATABASE.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/SQL_DATABASE.md) — Relational SQL schemas, index strategies, and data persistence.
- [APIS.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/APIS.md) — REST API specifications and WebSockets protocols.
