#!/usr/bin/env python3
"""
Seed Langfuse self-hosted instance with a default project and API keys.
Run this after Langfuse containers are healthy.
"""

import hashlib
import os
import secrets
import string
import sys

import bcrypt
import psycopg2

DB_URL = os.environ.get(
    "LANGFUSE_DATABASE_URL",
    "postgresql://postgres:postgres@postgres:5432/langfuse"
)

DEFAULT_USER_EMAIL = "admin@picocloth.local"
DEFAULT_USER_NAME = "PicoCloth Admin"
DEFAULT_USER_PASSWORD = "picocloth-admin-123"
DEFAULT_ORG_NAME = "PicoCloth Fleet"
DEFAULT_PROJECT_NAME = "picocloth-fleet"


def generate_cuid() -> str:
    """Generate a simple cuid-like ID."""
    prefix = "cm" + secrets.token_hex(8)
    return prefix


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def bcrypt_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()


def seed_langfuse():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Check if already seeded
    cur.execute("SELECT id FROM organizations WHERE name = %s", (DEFAULT_ORG_NAME,))
    if cur.fetchone():
        print("Langfuse already seeded. Skipping.")
        conn.close()
        return

    # Generate IDs
    user_id = generate_cuid()
    org_id = generate_cuid()
    project_id = generate_cuid()
    org_membership_id = generate_cuid()
    api_key_id = generate_cuid()

    # Generate API key pair
    public_key = "pk-lf-" + secrets.token_hex(16)
    raw_secret = "sk-lf-" + secrets.token_hex(32)
    display_secret = raw_secret[:8] + "..." + raw_secret[-4:]

    # Hash the secret key
    fast_hash = sha256_hex(raw_secret)
    slow_hash = bcrypt_hash(raw_secret)

    print(f"Creating user: {DEFAULT_USER_EMAIL}")
    print(f"Creating org: {DEFAULT_ORG_NAME}")
    print(f"Creating project: {DEFAULT_PROJECT_NAME}")
    print(f"Creating API key: {public_key}")
    print(f"  Secret: {raw_secret}")

    # 1. Create user
    cur.execute(
        """
        INSERT INTO users (id, name, email, email_verified, password, admin, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), %s, true, NOW(), NOW())
        ON CONFLICT (email) DO NOTHING
        """,
        (user_id, DEFAULT_USER_NAME, DEFAULT_USER_EMAIL, bcrypt_hash(DEFAULT_USER_PASSWORD)),
    )

    # 2. Create organization
    cur.execute(
        """
        INSERT INTO organizations (id, name, created_at, updated_at)
        VALUES (%s, %s, NOW(), NOW())
        """,
        (org_id, DEFAULT_ORG_NAME),
    )

    # 3. Create project
    cur.execute(
        """
        INSERT INTO projects (id, name, org_id, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        """,
        (project_id, DEFAULT_PROJECT_NAME, org_id),
    )

    # 4. Create organization membership
    cur.execute(
        """
        INSERT INTO organization_memberships (id, org_id, user_id, role, created_at, updated_at)
        VALUES (%s, %s, %s, 'OWNER', NOW(), NOW())
        """,
        (org_membership_id, org_id, user_id),
    )

    # 5. Create project membership
    cur.execute(
        """
        INSERT INTO project_memberships (project_id, user_id, org_membership_id, role, created_at, updated_at)
        VALUES (%s, %s, %s, 'OWNER', NOW(), NOW())
        """,
        (project_id, user_id, org_membership_id),
    )

    # 6. Create API key
    cur.execute(
        """
        INSERT INTO api_keys (
            id, public_key, hashed_secret_key, display_secret_key,
            fast_hashed_secret_key, project_id, organization_id, scope, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'PROJECT', NOW())
        """,
        (api_key_id, public_key, slow_hash, display_secret, fast_hash, project_id, org_id),
    )

    conn.commit()
    conn.close()

    # Write credentials to file
    creds_path = "/home/shivaramgoud/tinkering/tinkering-with-claws/picocloth/shared/state/langfuse-credentials.json"
    os.makedirs(os.path.dirname(creds_path), exist_ok=True)
    with open(creds_path, "w") as f:
        import json
        json.dump({
            "host": "http://localhost:3000",
            "public_key": public_key,
            "secret_key": raw_secret,
            "project_id": project_id,
            "org_id": org_id,
        }, f, indent=2)

    print(f"\n✅ Langfuse seeded successfully!")
    print(f"   Credentials saved to: {creds_path}")
    print("\n   Login: http://localhost:3000")
    print(f"   Email: {DEFAULT_USER_EMAIL}")
    print(f"   Password: {DEFAULT_USER_PASSWORD}")
    print(f"\n   API Key (public): {public_key}")
    print(f"   API Key (secret): {raw_secret}")

    # Test connection
    print("\n   Testing Langfuse connection...")
    try:
        from langfuse import Langfuse
        lf = Langfuse(public_key=public_key, secret_key=raw_secret, host="http://localhost:3000")
        lf.auth_check()
        print("   ✅ Langfuse auth check passed!")
    except Exception as e:
        print(f"   ⚠️  Auth check failed (hash mismatch?): {e}")
        print("   You may need to create API keys manually via the UI.")


if __name__ == "__main__":
    try:
        seed_langfuse()
    except psycopg2.OperationalError as e:
        print(f"ERROR: Cannot connect to Langfuse Postgres: {e}")
        print("Make sure Langfuse containers are running: cd langfuse && docker compose up -d")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
