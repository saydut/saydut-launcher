"""
Password Manager Database
SQLite database with AES-256-GCM encryption
"""
import os
import sqlite3
import secrets
import base64
from typing import Optional, List, Tuple

from shared import (
    PBKDF2_ITERATIONS,
    SALT_LENGTH,
    NONCE_LENGTH,
    derive_key_pbkdf2,
    constant_time_compare,
    encrypt_aes_gcm,
    decrypt_aes_gcm,
)


# ============================================================================
# DATABASE CLASS
# ============================================================================

class PassDB:
    """
    Password database with encryption

    Schema:
    - meta: key-value store (vault_salt, schema_version)
    - auth: master password hash
    - vault: encrypted password entries
    """

    def __init__(self, path: str):
        self.path = path
        self._ensure_db()

    def _conn(self) -> sqlite3.Connection:
        """Create database connection"""
        con = sqlite3.connect(self.path)
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA foreign_keys=ON;")
        return con

    def _ensure_db(self) -> None:
        """Create database tables if they don't exist"""
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)

        with self._conn() as con:
            # Meta table
            con.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Auth table (master password)
            con.execute("""
                CREATE TABLE IF NOT EXISTS auth (
                    id INTEGER PRIMARY KEY CHECK (id=1),
                    master_hash BLOB NOT NULL,
                    auth_salt BLOB NOT NULL,
                    kdf_iter INTEGER NOT NULL
                )
            """)

            # Vault table (encrypted entries)
            con.execute("""
                CREATE TABLE IF NOT EXISTS vault (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    blob BLOB NOT NULL,
                    nonce BLOB NOT NULL
                )
            """)

            # Schema version
            cur = con.execute("SELECT value FROM meta WHERE key='schema_version'")
            row = cur.fetchone()
            if not row:
                con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version','2')")

            # Vault salt
            cur = con.execute("SELECT value FROM meta WHERE key='vault_salt_b64'")
            row = cur.fetchone()
            if not row:
                vs = secrets.token_bytes(SALT_LENGTH)
                con.execute(
                    "INSERT OR REPLACE INTO meta(key,value) VALUES('vault_salt_b64', ?)",
                    (base64.b64encode(vs).decode("ascii"),)
                )

    # ========================================================================
    # MASTER PASSWORD
    # ========================================================================

    def has_master(self) -> bool:
        """Check if master password is set"""
        with self._conn() as con:
            cur = con.execute("SELECT 1 FROM auth WHERE id=1")
            return cur.fetchone() is not None

    def set_master(self, password: str) -> None:
        """Set/change master password"""
        auth_salt = secrets.token_bytes(SALT_LENGTH)
        master_hash = derive_key_pbkdf2(password, auth_salt, PBKDF2_ITERATIONS)

        with self._conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO auth(id, master_hash, auth_salt, kdf_iter) VALUES(1, ?, ?, ?)",
                (master_hash, auth_salt, PBKDF2_ITERATIONS)
            )

    def verify_master(self, password: str) -> bool:
        """Verify master password"""
        with self._conn() as con:
            cur = con.execute("SELECT master_hash, auth_salt, kdf_iter FROM auth WHERE id=1")
            row = cur.fetchone()
            if not row:
                return False

            stored_hash, auth_salt, iterations = row
            computed_hash = derive_key_pbkdf2(password, auth_salt, iterations)
            return constant_time_compare(computed_hash, stored_hash)

    # ========================================================================
    # VAULT OPERATIONS
    # ========================================================================

    def _get_vault_salt(self) -> bytes:
        """Get vault encryption salt"""
        with self._conn() as con:
            cur = con.execute("SELECT value FROM meta WHERE key='vault_salt_b64'")
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Vault salt not found")
            return base64.b64decode(row[0])

    def _derive_vault_key(self, password: str) -> bytes:
        """Derive vault encryption key from master password"""
        vault_salt = self._get_vault_salt()
        return derive_key_pbkdf2(password, vault_salt, PBKDF2_ITERATIONS)

    def add_entry(
        self,
        master_password: str,
        site: str,
        username: str,
        password: str,
        notes: str = ""
    ) -> int:
        """
        Add password entry

        Args:
            master_password: Master password for encryption
            site: Website/service name
            username: Username
            password: Password
            notes: Optional notes

        Returns:
            int: Entry ID

        Raises:
            Exception: If encryption fails
        """
        vault_key = self._derive_vault_key(master_password)

        # Build plaintext JSON
        import json
        plaintext = json.dumps({
            "site": site,
            "username": username,
            "password": password,
            "notes": notes
        }).encode("utf-8")

        # Encrypt
        ciphertext, nonce = encrypt_aes_gcm(plaintext, vault_key)

        # Store
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO vault(blob, nonce) VALUES(?, ?)",
                (ciphertext, nonce)
            )
            return cur.lastrowid

    def get_all_entries(self, master_password: str) -> List[Tuple[int, str, str, str, str]]:
        """
        Get all password entries

        Args:
            master_password: Master password for decryption

        Returns:
            List of (entry_id, site, username, password, notes)

        Raises:
            Exception: If decryption fails (wrong password)
        """
        vault_key = self._derive_vault_key(master_password)

        with self._conn() as con:
            cur = con.execute("SELECT entry_id, blob, nonce FROM vault")
            rows = cur.fetchall()

        entries = []
        import json

        for entry_id, blob, nonce in rows:
            try:
                plaintext = decrypt_aes_gcm(blob, vault_key, nonce)
                data = json.loads(plaintext.decode("utf-8"))

                entries.append((
                    entry_id,
                    data.get("site", ""),
                    data.get("username", ""),
                    data.get("password", ""),
                    data.get("notes", "")
                ))
            except Exception as e:
                print(f"Failed to decrypt entry {entry_id}: {e}")
                continue

        return entries

    def delete_entry(self, entry_id: int) -> None:
        """Delete password entry"""
        with self._conn() as con:
            con.execute("DELETE FROM vault WHERE entry_id=?", (entry_id,))

    def update_entry(
        self,
        entry_id: int,
        master_password: str,
        site: str,
        username: str,
        password: str,
        notes: str = ""
    ) -> None:
        """Update password entry"""
        vault_key = self._derive_vault_key(master_password)

        # Build plaintext JSON
        import json
        plaintext = json.dumps({
            "site": site,
            "username": username,
            "password": password,
            "notes": notes
        }).encode("utf-8")

        # Encrypt
        ciphertext, nonce = encrypt_aes_gcm(plaintext, vault_key)

        # Update
        with self._conn() as con:
            con.execute(
                "UPDATE vault SET blob=?, nonce=? WHERE entry_id=?",
                (ciphertext, nonce, entry_id)
            )

    def count_entries(self) -> int:
        """Get total entry count"""
        with self._conn() as con:
            cur = con.execute("SELECT COUNT(*) FROM vault")
            return cur.fetchone()[0]
