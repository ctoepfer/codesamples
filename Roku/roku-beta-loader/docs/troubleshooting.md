# Troubleshooting

## Roku Not Found

Make sure your computer and Roku are on the same Wi-Fi or wired network. Disable VPNs temporarily if they block local network traffic. Some guest Wi-Fi networks block device-to-device traffic.

## Developer Installer Does Not Open

Confirm Developer Mode is enabled and the Roku finished restarting after setup. Visit `http://ROKU_IP` in a browser to check whether the developer installer responds.

## Wrong Password

The username is usually `rokudev`. The password is the one set during Developer Mode setup. This tool does not store passwords.

## Invalid Checksum

Do not install the zip if the SHA-256 does not match the release manifest. Download again or contact support.

## Upload Failed

Confirm the Roku is still reachable, Developer Mode is enabled, the password is correct, and only one install attempt is running.
