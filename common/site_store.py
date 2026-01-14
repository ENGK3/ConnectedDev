#!/usr/bin/env python3
"""
Decrypt site_info file using public key (verification pattern).
This assumes the file was encrypted/signed with the private key.
"""

import subprocess
from pathlib import Path


def decrypt_with_public_key(encrypted_file_path: str, public_key_path: str) -> str:
    """
    Decrypt/verify a file that was encrypted/signed with a private key.

    This uses OpenSSL's rsautl -verify operation, which is the proper way
    to decrypt data that was "encrypted" (signed) with a private key.

    Args:
        encrypted_file_path: Path to the encrypted file
        public_key_path: Path to the public key file

    Returns:
        Decrypted contents as a string

    Raises:
        FileNotFoundError: If encrypted file or public key doesn't exist
        subprocess.CalledProcessError: If decryption fails
    """
    # Verify files exist
    if not Path(encrypted_file_path).exists():
        raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")

    if not Path(public_key_path).exists():
        raise FileNotFoundError(f"Public key not found: {public_key_path}")

    # Use OpenSSL to decrypt/verify with public key
    # Note: rsautl is deprecated but still widely used. For newer OpenSSL, pkeyutl can
    # be used
    try:
        result = subprocess.run(
            [
                "openssl",
                "rsautl",
                "-verify",
                "-pubin",
                "-inkey",
                public_key_path,
                "-in",
                encrypted_file_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        # Try with pkeyutl for newer OpenSSL versions
        try:
            result = subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-verifyrecover",
                    "-pubin",
                    "-inkey",
                    public_key_path,
                    "-in",
                    encrypted_file_path,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError:
            # Re-raise the original error
            raise e from None


def decrypt_site_store(
    site_store_path: str = "/mnt/data/site_info",
    public_key_path: str = "/mnt/data/site.pub",
) -> str:
    """
    Convenience function to decrypt the site_info file.

    Args:
        site_store_path: Path to the encrypted site_info file
        (default: /mnt/data/site_info)
        public_key_path: Path to the public key (default: /mnt/data/site.pub)

    Returns:
        Decrypted contents as a string

    Raises:
        FileNotFoundError: If site_store or public key doesn't exist
        subprocess.CalledProcessError: If decryption fails
    """
    return decrypt_with_public_key(site_store_path, public_key_path)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Decrypt site_store file using public key"
    )
    parser.add_argument(
        "encrypted_file",
        nargs="?",
        default="/mnt/data/site_store",
        help="Path to encrypted file (default: /mnt/data/site_store)",
    )
    parser.add_argument(
        "public_key",
        nargs="?",
        default="/mnt/data/site.pub",
        help="Path to public key (default: /mnt/data/site.pub)",
    )

    args = parser.parse_args()

    try:
        contents = decrypt_site_store(args.encrypted_file, args.public_key)
        print(contents)
    except Exception as e:
        print(f"Error decrypting file: {e}", file=sys.stderr)
        sys.exit(1)
