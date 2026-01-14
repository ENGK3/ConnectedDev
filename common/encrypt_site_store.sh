#!/bin/bash
# Encrypt a file using private key and save to site_store
# This uses RSA signing operation to "encrypt" with the private key

encrypt_with_private_key() {
    local input_file="$1"
    local private_key="${2:-/mnt/data/site.priv}"
    local output_file="${3:-/mnt/data/site_store}"

    # Validate arguments
    if [ -z "$input_file" ]; then
        echo "Usage: encrypt_with_private_key <input_file> [private_key] [output_file]" >&2
        echo "  input_file:   File to encrypt (required)" >&2
        echo "  private_key:  Path to private key (default: /mnt/data/site.priv)" >&2
        echo "  output_file:  Output path (default: /mnt/data/site_store)" >&2
        return 1
    fi

    if [ ! -f "$input_file" ]; then
        echo "Error: Input file '$input_file' not found" >&2
        return 1
    fi

    if [ ! -f "$private_key" ]; then
        echo "Error: Private key '$private_key' not found" >&2
        return 1
    fi

    # Ensure output directory exists
    local output_dir=$(dirname "$output_file")
    if [ ! -d "$output_dir" ]; then
        mkdir -p "$output_dir" || {
            echo "Error: Failed to create output directory '$output_dir'" >&2
            return 1
        }
    fi

    # Encrypt/sign with private key
    # Try rsautl first (older but widely compatible)
    if openssl rsautl -sign -inkey "$private_key" -in "$input_file" -out "$output_file" 2>/dev/null; then
        echo "Successfully encrypted '$input_file' to '$output_file' using rsautl"
        return 0
    fi

    # If rsautl fails, try pkeyutl (newer method)
    if openssl pkeyutl -sign -inkey "$private_key" -in "$input_file" -out "$output_file" 2>/dev/null; then
        echo "Successfully encrypted '$input_file' to '$output_file' using pkeyutl"
        return 0
    fi

    echo "Error: Encryption failed with both rsautl and pkeyutl" >&2
    return 1
}

# If script is executed (not sourced), run the function
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    encrypt_with_private_key "$@"
fi
