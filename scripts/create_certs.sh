#!/bin/bash

# You will need to install open ssh!

domain="*"
output_dir="<YOUR_PATH>/certs"

# Generate private key and certificate
openssl req -newkey rsa:2048 -nodes -keyout "$output_dir/key.pem" -x509 -days 365 -out "$output_dir/certificate.crt" -subj "/CN=$domain"

# Create PEM file with private key and certificate
cat "$output_dir/key.pem" "$output_dir/certificate.crt" > "$output_dir/certificate.pem"

echo "SSL self-signed certificate, private key, and PEM file generated successfully!"
echo "Private key: $output_dir/key.pem"
echo "Certificate: $output_dir/certificate.crt"
echo "PEM file: $output_dir/certificate.pem"
