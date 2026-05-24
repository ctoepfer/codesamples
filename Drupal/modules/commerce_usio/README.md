# Commerce USIO

Drupal Commerce payment gateway module for [USIO Payments](https://usiopay.com), using the USIO Checkout.js embedded tokenisation flow.

> **Status:** Community / code-sample module. Test thoroughly in a sandboxed environment before using in production. See [Security](#security) notes below.

---

## Contents

- [Requirements](#requirements)
- [How it works](#how-it-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Environment variables (recommended for production)](#environment-variables-recommended-for-production)
- [Security](#security)
- [Testing with sandbox credentials](#testing-with-sandbox-credentials)
- [Troubleshooting](#troubleshooting)
- [Compatibility](#compatibility)
- [License](#license)

---

## Requirements

| Dependency | Version |
|---|---|
| PHP | 8.1 or higher |
| Drupal core | 10 or 11 |
| Drupal Commerce | 2.x |
| Guzzle HTTP client | ships with Drupal core |

You will also need an active [USIO merchant account](https://usiopay.com) with Checkout 2.0 API access.

---

## How it works

1. During checkout, the module loads **USIO Checkout.js** from USIO's CDN into an embedded iframe inside the Drupal Commerce payment form.
2. The customer enters card details directly in the USIO-hosted iframe — card data never touches your server, minimising PCI scope.
3. When the customer submits the iframe form, USIO posts a **one-time payment token** back to the page via `window.postMessage`.
4. The module's JavaScript captures the token, stores it in a hidden form field, and re-submits the Drupal Commerce form.
5. Server-side, the module calls USIO's `SubmitTokenPayment` REST endpoint with the token and the order's billing information.
6. On success, Drupal Commerce records the confirmed payment and advances the order.

Refunds are supported through the admin UI via USIO's `RefundTransaction` endpoint.

---

## Installation

### Via Drupal admin (manual)

1. Copy the `commerce_usio` directory into your Drupal installation at `web/modules/custom/commerce_usio/`.
2. Navigate to **Extend** (`/admin/modules`) and enable **Commerce USIO**.
3. Or use Drush: `drush en commerce_usio -y && drush cr`

### Via Composer (local path repository)

If you have cloned this repository locally, you can add it to your project's `composer.json` as a path repository:

```json
{
    "repositories": [
        {
            "type": "path",
            "url": "/path/to/codesamples/Drupal/modules/commerce_usio"
        }
    ]
}
```

Then require the package:

```bash
composer require ctoepfer/commerce_usio
```

> **Note:** Because `composer.json` lives inside a subdirectory of the `codesamples` repository (not at its root), Composer VCS repository support cannot resolve it directly from the GitHub URL. Use a local path repository, or host the module in its own dedicated repository for full Composer VCS support.

---

## Configuration

1. Go to **Commerce → Configuration → Payment gateways** (`/admin/commerce/config/payment-gateways`).
2. Click **Add payment gateway**.
3. Choose **USIO** from the plugin list.
4. Fill in the credential fields:

| Field | Description |
|---|---|
| **Merchant ID** | Your USIO Merchant ID (numeric, e.g. provided by USIO) |
| **API Login / User ID** | Your USIO API Login or User ID |
| **API Password** | Your USIO API password — see [security note](#security) below |
| **Merchant Key** | Your USIO client-side `ApiKey` / Merchant Key (used by Checkout.js) |
| **Terminal ID** | Optional. Your USIO Terminal ID |
| **Mode** | Select **Sandbox** for testing or **Live** for production |

5. Save. The gateway will appear on your checkout payment form.

---

## Environment variables (recommended for production)

Storing credentials in the Drupal database means they appear in database dumps and config exports. For production deployments, set these environment variables instead and **leave the corresponding form fields blank**:

```bash
USIO_MERCHANT_ID=your_merchant_id
USIO_LOGIN=your_api_login
USIO_PASSWORD=your_api_password
USIO_TERMINAL_ID=your_terminal_id     # optional
USIO_MERCHANT_KEY=your_merchant_key   # client-side Checkout.js ApiKey
```

The module checks for these variables at runtime and falls back to the stored database values only when the variables are not set.

> **Note on `USIO_MERCHANT_KEY`:** Unlike the server-side credentials, the Merchant Key is sent to the browser to initialise the USIO Checkout.js iframe (analogous to Stripe's publishable key). It is intentionally semi-public. However, you should still supply it via an environment variable rather than committing it to version control, and you should avoid including it in `drush cex` exports.

In DDEV, add them to `.ddev/.env` (gitignored). In production, set them in your server environment, Docker Compose, or a secrets manager.

---

## Security

- **Do not commit real credentials** to version control.  
- **Do not run `drush cex`** with production credentials stored in the database — the export will include them in plain-text YAML files.
- The API password field uses `#type => 'password'` and is never pre-populated in the form, but it is stored in plain text in the Drupal database. Use environment variables for production (see above).
- The **Merchant Key** (`ApiKey`) is intentionally sent to the browser to initialise the USIO Checkout.js iframe. Treat it as a semi-public client-side key (analogous to Stripe's publishable key). Supply it via `USIO_MERCHANT_KEY` so it stays out of version control and `drush cex` exports.
- API request/response bodies are **never logged**. Only the HTTP status code and endpoint name are written to the Drupal log on failure, to avoid leaking customer PII or credentials.
- WCAG 2.1 Level AA accessibility is applied to all form elements and error regions.

---

## Testing with sandbox credentials

USIO provides a sandbox environment at `https://devcheckout.usiopay.com/2.0/`. When the gateway is set to **Sandbox** mode, the module automatically uses the sandbox Checkout.js URL and sandbox API endpoint.

USIO publishes example sandbox credentials in their developer documentation. Use those credentials — not real ones — for all development and testing work.

A basic test card (from USIO sandbox docs): `4111 1111 1111 1111`, any future expiry, any CVV.

---

## Troubleshooting

**The iframe does not appear on the payment form.**  
Check your browser console for JavaScript errors. Verify that the Merchant Key is correctly configured, and that your Content Security Policy allows `frame-src` and `script-src` for `*.usiopay.com`.

**Payment fails with "No response received from the USIO payment gateway."**  
Check Drupal's watchdog log (`/admin/reports/dblog`) for HTTP error codes. Verify credentials and network access from your server to `checkout.usiopay.com` (production) or `devcheckout.usiopay.com` (sandbox).

**Drush cannot enable the module (`Class "DOMDocument" does not exist`).**  
The CLI PHP binary is missing the `dom` extension. Enable the module through the Drupal admin UI at `/admin/modules`, or run Drush via the environment that has a full PHP installation (e.g. `ddev drush en commerce_usio -y` from outside the DDEV container).

**Config export (`drush cex`) shows credentials in YAML.**  
Switch to environment variables (see above) and delete the stored credential values from the gateway configuration form before running `drush cex`.

---

## Compatibility

| Item | Version |
|---|---|
| Drupal | 10.x, 11.x |
| Drupal Commerce | 2.x |
| PHP | 8.1, 8.2, 8.3 |
| USIO Checkout API | 2.0 |

---

## License

MIT — see [LICENSE](../../../LICENSE) or [https://opensource.org/licenses/MIT](https://opensource.org/licenses/MIT).

This module is a code sample. It is **not** an official USIO product and is **not** affiliated with USIO Payments.
