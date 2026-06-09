# Roku Developer Mode

Developer Mode is enabled manually on the Roku device with the Roku remote. This tool only guides the tester; it does not automate or bypass Roku's Developer Mode process.

General flow:

1. Use Roku's Developer Mode remote sequence.
2. Read and accept Roku's on-device prompts.
3. Set the developer web server password.
4. Keep the username as `rokudev` unless your app config says otherwise.
5. Restart the Roku when prompted.

After Developer Mode is enabled, the developer installer is available on the Roku device's local IP address. The computer running this tool must be able to reach that IP on the local network.
