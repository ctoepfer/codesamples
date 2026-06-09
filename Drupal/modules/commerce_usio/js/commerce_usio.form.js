/**
 * @file
 * Integrates USIO Checkout.js with the Drupal Commerce payment method form.
 *
 * Flow:
 *  1. LoadCheckout() is called with the merchant key, mounting a secure
 *     USIO-hosted iframe inside #usio-checkout-container.
 *  2. When the user submits the iframe form, USIO posts a message to this page
 *     containing a one-time payment token (and optional card metadata).
 *  3. The token is written to #usio-token (a hidden field).
 *  4. The Drupal form is re-submitted so PHP can call createPaymentMethod().
 */
(($, Drupal, drupalSettings, once) => {
  'use strict';

  Drupal.behaviors.commerceUsioForm = {

    /**
     * Whether we are currently awaiting a token from the USIO iframe.
     */
    _awaitingToken: false,

    /**
     * Bound reference to the message handler so we can remove it on detach.
     */
    _messageHandler: null,

    attach(context) {
      const settings = drupalSettings.commerceUsio;
      if (!settings || !settings.merchantKey) {
        return;
      }

      once('usio-form', '.usio-payment-form', context).forEach((formEl) => {
        const $form      = $(formEl).closest('form');
        const $container = $('#usio-checkout-container', $form);
        const $tokenField  = $('#usio-token', $form);
        const $errorRegion = $('#usio-payment-errors', $form);

        if (!$container.length || !$tokenField.length) {
          return;
        }

        // ── Helper: show an accessible error ──────────────────────────────
        const showError = (msg) => {
          $errorRegion
            .text(msg)
            .removeAttr('hidden')
            .show();
          $form.find(':input.button--primary').prop('disabled', false);
          this._awaitingToken = false;
        };

        const clearError = () => {
          $errorRegion.attr('hidden', true).hide().text('');
        };

        // ── postMessage listener ───────────────────────────────────────────
        // USIO sends a message when the iframe form is submitted successfully.
        // The exact shape varies between API versions; we handle common forms.
        this._messageHandler = (event) => {
          let data = event.data;

          // Some environments stringify the message.
          if (typeof data === 'string') {
            try { data = JSON.parse(data); } catch (_) { return; }
          }

          if (!data || typeof data !== 'object') {
            return;
          }

          // Extract token — USIO may use different field names.
          const token =
            data.Token        ||
            data.token        ||
            data.CardToken    ||
            data.PaymentToken ||
            null;

          // If there is an explicit error without a token, surface it.
          const error =
            data.Error        ||
            data.error        ||
            data.ErrorMessage ||
            data.Message      ||
            null;

          if (!token) {
            if (error && this._awaitingToken) {
              showError(
                Drupal.t('Payment error: @msg', { '@msg': error })
              );
            }
            return;
          }

          // ── Token received ─────────────────────────────────────────────
          clearError();
          $tokenField.val(token);

          // Optional card metadata — populate hidden fields when available.
          if (data.CardType || data.cardType) {
            $('#usio-card-type', $form).val(data.CardType || data.cardType);
          }
          if (data.Last4 || data.last4 || data.LastFour) {
            $('#usio-last4', $form).val(data.Last4 || data.last4 || data.LastFour);
          }
          if (data.ExpMonth || data.expMonth) {
            $('#usio-exp-month', $form).val(data.ExpMonth || data.expMonth);
          }
          if (data.ExpYear || data.expYear) {
            $('#usio-exp-year', $form).val(data.ExpYear || data.expYear);
          }

          // Re-submit the Drupal form now that the token is present.
          this._awaitingToken = false;
          $form.find(':input.button--primary').trigger('click');
        };

        window.addEventListener('message', this._messageHandler);

        // ── Initialise USIO Checkout.js ────────────────────────────────────
        // LoadCheckout() is provided by the externally-loaded checkout.js.
        const initCheckout = () => {
          if (typeof LoadCheckout !== 'function') {
            Drupal.behaviors.commerceUsioForm._scheduleRetry(initCheckout);
            return;
          }

          try {
            /* global LoadCheckout */
            LoadCheckout({
              ApiKey: settings.merchantKey,
            });
          }
          catch (e) {
            showError(
              Drupal.t('Could not initialise the payment form. Please refresh the page and try again.')
            );
            Drupal.behaviors.commerceUsioForm._log(e);
          }
        };

        initCheckout();

        // ── Intercept Drupal form submission ───────────────────────────────
        $form.on('submit.commerce_usio', () => {
          // If the token is already populated (e.g. after postMessage re-submit),
          // let the form through.
          if ($tokenField.val()) {
            return true;
          }

          // The USIO iframe handles its own submit button. If the Drupal submit
          // button is clicked before the token arrives, we block the Drupal
          // submission and wait for USIO to post the token.
          this._awaitingToken = true;
          clearError();

          // Prevent the default Drupal form submit until we have the token.
          return false;
        });
      });
    },

    detach(context, settings, trigger) {
      if (trigger !== 'unload') {
        return;
      }

      if (this._messageHandler) {
        window.removeEventListener('message', this._messageHandler);
        this._messageHandler = null;
      }

      const $form = $('.usio-payment-form', context).closest('form');
      if ($form.length) {
        $form.off('submit.commerce_usio');
      }
    },

    /**
     * Retries a callback after a short delay (LoadCheckout may not be ready).
     */
    _scheduleRetry(fn, attempt) {
      attempt = attempt || 0;
      if (attempt > 20) {
        Drupal.behaviors.commerceUsioForm._log('USIO checkout.js did not load in time.');
        return;
      }
      setTimeout(() => fn(attempt + 1), 250);
    },

    _log(msg) {
      if (window.console && console.warn) {
        console.warn('[commerce_usio]', msg);
      }
    },
  };

})(jQuery, Drupal, drupalSettings, once);
