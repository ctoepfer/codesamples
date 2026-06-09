# Tester Guide

Use this utility when you have been invited to test a Roku beta channel before it is publicly listed.

1. Enable Developer Mode on your Roku.
2. Make sure your computer and Roku are on the same network.
3. Run `roku-beta-loader roku discover` to find the Roku.
4. Run `roku-beta-loader install --config PATH --ip ROKU_IP --password PASSWORD`.

Installing a beta replaces the current sideloaded channel on the Roku. It does not replace public Roku Channel Store apps.
