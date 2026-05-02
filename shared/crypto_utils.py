"""
Cryptography Utilities for Saydut Launcher
Shared crypto functions for Encrypter, Password Manager modules

Uses AES-256-GCM for encryption and PBKDF2-HMAC-SHA256 for key derivation
"""
import os
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


# ============================================================================
# CONSTANTS
# ============================================================================

# PBKDF2 iterations (260k is good balance between security and performance)
# Increase for higher security, decrease for faster key derivation
PBKDF2_ITERATIONS = 260_000

# Key length for AES-256
KEY_LENGTH = 32  # 256 bits

# Nonce length for AES-GCM
NONCE_LENGTH = 12  # 96 bits (recommended for GCM)

# Salt length for PBKDF2
SALT_LENGTH = 16  # 128 bits


# ============================================================================
# KEY DERIVATION
# ============================================================================

def derive_key_pbkdf2(
    password: str,
    salt: bytes,
    iterations: int = PBKDF2_ITERATIONS
) -> bytes:
    """
    Derive encryption key from password using PBKDF2-HMAC-SHA256

    Args:
        password: User password (will be encoded to UTF-8)
        salt: Random salt (should be 16+ bytes)
        iterations: Number of PBKDF2 iterations (default 260,000)

    Returns:
        bytes: 32-byte encryption key for AES-256

    Example:
        salt = os.urandom(16)
        key = derive_key_pbkdf2("my_password", salt)
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )
    return kdf.derive(password.encode('utf-8'))


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """
    Constant-time byte comparison (prevents timing attacks)

    Args:
        a: First byte string
        b: Second byte string

    Returns:
        bool: True if equal, False otherwise
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b):
        result |= x ^ y

    return result == 0


# ============================================================================
# AES-GCM ENCRYPTION/DECRYPTION
# ============================================================================

def encrypt_aes_gcm(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes]:
    """
    Encrypt data using AES-256-GCM

    GCM provides both encryption and authentication (no separate MAC needed).

    Args:
        plaintext: Data to encrypt
        key: 32-byte encryption key

    Returns:
        Tuple[bytes, bytes]: (ciphertext with tag, nonce)

    Example:
        key = derive_key_pbkdf2("password", salt)
        ciphertext, nonce = encrypt_aes_gcm(b"secret data", key)
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_LENGTH)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)  # No AAD
    return ciphertext, nonce


def decrypt_aes_gcm(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    """
    Decrypt data using AES-256-GCM

    Automatically verifies authentication tag.

    Args:
        ciphertext: Encrypted data (includes 16-byte auth tag at end)
        key: 32-byte encryption key
        nonce: 12-byte nonce used during encryption

    Returns:
        bytes: Decrypted plaintext

    Raises:
        cryptography.exceptions.InvalidTag: If authentication fails

    Example:
        plaintext = decrypt_aes_gcm(ciphertext, key, nonce)
    """
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext


# ============================================================================
# HIGH-LEVEL FILE ENCRYPTION
# ============================================================================

def encrypt_file(input_path: str, output_path: str, password: str) -> None:
    """
    Encrypt a file with password

    File format:
    [salt: 16 bytes][nonce: 12 bytes][ciphertext + tag: variable]

    Args:
        input_path: Path to file to encrypt
        output_path: Path to write encrypted file
        password: Encryption password

    Raises:
        FileNotFoundError: If input file doesn't exist
        PermissionError: If cannot write to output

    Example:
        encrypt_file("document.pdf", "document.pdf.enc", "my_password")
    """
    # Read plaintext
    with open(input_path, 'rb') as f:
        plaintext = f.read()

    # Generate random salt
    salt = os.urandom(SALT_LENGTH)

    # Derive key from password
    key = derive_key_pbkdf2(password, salt)

    # Encrypt
    ciphertext, nonce = encrypt_aes_gcm(plaintext, key)

    # Write: salt + nonce + ciphertext
    with open(output_path, 'wb') as f:
        f.write(salt)
        f.write(nonce)
        f.write(ciphertext)


def decrypt_file(input_path: str, output_path: str, password: str) -> None:
    """
    Decrypt a file with password

    Args:
        input_path: Path to encrypted file
        output_path: Path to write decrypted file
        password: Decryption password

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If file format is invalid
        cryptography.exceptions.InvalidTag: If password is wrong

    Example:
        decrypt_file("document.pdf.enc", "document.pdf", "my_password")
    """
    # Read encrypted file
    with open(input_path, 'rb') as f:
        data = f.read()

    # Validate minimum size
    min_size = SALT_LENGTH + NONCE_LENGTH + 16  # +16 for GCM tag
    if len(data) < min_size:
        raise ValueError(
            f"File too small ({len(data)} bytes). "
            f"Expected at least {min_size} bytes."
        )

    # Extract components
    salt = data[:SALT_LENGTH]
    nonce = data[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
    ciphertext = data[SALT_LENGTH + NONCE_LENGTH:]

    # Derive key from password
    key = derive_key_pbkdf2(password, salt)

    # Decrypt (raises InvalidTag if password wrong)
    plaintext = decrypt_aes_gcm(ciphertext, key, nonce)

    # Write plaintext
    with open(output_path, 'wb') as f:
        f.write(plaintext)


def encrypt_bytes(data: bytes, password: str) -> bytes:
    """
    Encrypt bytes with password (returns encrypted bytes)

    Format: [salt: 16][nonce: 12][ciphertext + tag]

    Args:
        data: Data to encrypt
        password: Encryption password

    Returns:
        bytes: Encrypted data (salt + nonce + ciphertext)

    Example:
        encrypted = encrypt_bytes(b"secret", "password")
    """
    salt = os.urandom(SALT_LENGTH)
    key = derive_key_pbkdf2(password, salt)
    ciphertext, nonce = encrypt_aes_gcm(data, key)

    return salt + nonce + ciphertext


def decrypt_bytes(encrypted_data: bytes, password: str) -> bytes:
    """
    Decrypt bytes with password

    Args:
        encrypted_data: Encrypted data (salt + nonce + ciphertext)
        password: Decryption password

    Returns:
        bytes: Decrypted data

    Raises:
        ValueError: If data format is invalid
        cryptography.exceptions.InvalidTag: If password is wrong

    Example:
        decrypted = decrypt_bytes(encrypted, "password")
    """
    min_size = SALT_LENGTH + NONCE_LENGTH + 16
    if len(encrypted_data) < min_size:
        raise ValueError(f"Encrypted data too small ({len(encrypted_data)} bytes)")

    salt = encrypted_data[:SALT_LENGTH]
    nonce = encrypted_data[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
    ciphertext = encrypted_data[SALT_LENGTH + NONCE_LENGTH:]

    key = derive_key_pbkdf2(password, salt)
    plaintext = decrypt_aes_gcm(ciphertext, key, nonce)

    return plaintext


# ============================================================================
# FOLDER ENCRYPTION (FOR ENCRYPTER MODULE)
# ============================================================================

def encrypt_folder(
    folder_path: str,
    password: str,
    progress_callback=None
) -> Tuple[int, int]:
    """
    Encrypt all files in a folder recursively

    Original files are deleted after successful encryption.

    Args:
        folder_path: Path to folder
        password: Encryption password
        progress_callback: Optional callback(current, total, filename)

    Returns:
        Tuple[int, int]: (success_count, error_count)

    Example:
        success, errors = encrypt_folder("/path/to/folder", "password")
        print(f"Encrypted: {success}, Errors: {errors}")
    """
    import os as _os

    success_count = 0
    error_count = 0

    # Count total files first (for progress)
    total_files = sum(
        len([f for f in files if not f.endswith('.enc')])
        for _, _, files in _os.walk(folder_path)
    )

    current = 0

    for root, _, files in _os.walk(folder_path):
        for filename in files:
            # Skip already encrypted files
            if filename.endswith('.enc'):
                continue

            file_path = _os.path.join(root, filename)
            encrypted_path = file_path + '.enc'

            try:
                current += 1

                # Progress callback
                if progress_callback:
                    progress_callback(current, total_files, filename)

                # Encrypt file
                encrypt_file(file_path, encrypted_path, password)

                # Delete original
                _os.remove(file_path)

                success_count += 1

            except Exception as e:
                print(f"Error encrypting {file_path}: {e}")
                error_count += 1

    return success_count, error_count


def decrypt_folder(
    folder_path: str,
    password: str,
    progress_callback=None
) -> Tuple[int, int]:
    """
    Decrypt all .enc files in a folder recursively

    Encrypted files are deleted after successful decryption.

    Args:
        folder_path: Path to folder
        password: Decryption password
        progress_callback: Optional callback(current, total, filename)

    Returns:
        Tuple[int, int]: (success_count, error_count)

    Example:
        success, errors = decrypt_folder("/path/to/folder", "password")
    """
    import os as _os

    success_count = 0
    error_count = 0

    # Count .enc files
    total_files = sum(
        len([f for f in files if f.endswith('.enc')])
        for _, _, files in _os.walk(folder_path)
    )

    current = 0

    for root, _, files in _os.walk(folder_path):
        for filename in files:
            # Only decrypt .enc files
            if not filename.endswith('.enc'):
                continue

            encrypted_path = _os.path.join(root, filename)
            decrypted_path = encrypted_path[:-4]  # Remove .enc

            try:
                current += 1

                # Progress callback
                if progress_callback:
                    progress_callback(current, total_files, filename)

                # Decrypt file
                decrypt_file(encrypted_path, decrypted_path, password)

                # Delete encrypted file
                _os.remove(encrypted_path)

                success_count += 1

            except Exception as e:
                print(f"Error decrypting {encrypted_path}: {e}")
                error_count += 1

    return success_count, error_count
