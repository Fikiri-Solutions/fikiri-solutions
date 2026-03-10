<?php
/**
 * Fikiri WordPress Integration Example
 * 
 * Add this to your WordPress theme's functions.php or create a custom plugin
 */

// Add Fikiri SDK to footer
function fikiri_add_sdk() {
    $api_key = get_option('fikiri_api_key', ''); // Get from WordPress options
    if (empty($api_key)) {
        return; // Don't load if API key not configured
    }
    ?>
    <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
    <script>
        Fikiri.init({
            apiKey: '<?php echo esc_js($api_key); ?>',
            features: ['chatbot', 'leadCapture']
        });
        
        // Show chatbot after page load
        window.addEventListener('load', function() {
            Fikiri.Chatbot.show();
        });
    </script>
    <?php
}
add_action('wp_footer', 'fikiri_add_sdk');

// Shortcode for chatbot
function fikiri_chatbot_shortcode($atts) {
    $api_key = get_option('fikiri_api_key', '');
    if (empty($api_key)) {
        return '<p>Fikiri API key not configured.</p>';
    }
    
    $atts = shortcode_atts(array(
        'theme' => 'light',
        'position' => 'bottom-right'
    ), $atts);
    
    ob_start();
    ?>
    <script>
        if (typeof Fikiri === 'undefined') {
            // Load SDK if not already loaded
            var script = document.createElement('script');
            script.src = 'https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js';
            script.onload = function() {
                Fikiri.init({
                    apiKey: '<?php echo esc_js($api_key); ?>'
                });
                Fikiri.Chatbot.show({
                    theme: '<?php echo esc_js($atts['theme']); ?>',
                    position: '<?php echo esc_js($atts['position']); ?>'
                });
            };
            document.head.appendChild(script);
        } else {
            Fikiri.Chatbot.show({
                theme: '<?php echo esc_js($atts['theme']); ?>',
                position: '<?php echo esc_js($atts['position']); ?>'
            });
        }
    </script>
    <?php
    return ob_get_clean();
}
add_shortcode('fikiri_chatbot', 'fikiri_chatbot_shortcode');

// Shortcode for lead capture form
function fikiri_lead_capture_shortcode($atts) {
    $api_key = get_option('fikiri_api_key', '');
    if (empty($api_key)) {
        return '<p>Fikiri API key not configured.</p>';
    }
    
    $atts = shortcode_atts(array(
        'fields' => 'email,name'
    ), $atts);
    
    ob_start();
    ?>
    <form id="fikiri-lead-form" style="max-width: 400px; margin: 20px 0;">
        <h3>Get in Touch</h3>
        <?php if (strpos($atts['fields'], 'name') !== false): ?>
        <p>
            <label>Name:</label><br>
            <input type="text" id="fikiri-name" required style="width: 100%; padding: 8px;">
        </p>
        <?php endif; ?>
        <p>
            <label>Email:</label><br>
            <input type="email" id="fikiri-email" required style="width: 100%; padding: 8px;">
        </p>
        <p>
            <button type="submit" style="padding: 10px 20px; background: #0f766e; color: white; border: none; cursor: pointer;">
                Submit
            </button>
        </p>
        <div id="fikiri-form-message" style="margin-top: 10px;"></div>
    </form>
    <script>
        document.getElementById('fikiri-lead-form').addEventListener('submit', function(e) {
            e.preventDefault();
            var email = document.getElementById('fikiri-email').value;
            var name = document.getElementById('fikiri-name')?.value || '';
            
            fetch('https://api.fikirisolutions.com/api/webhooks/leads/capture', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': '<?php echo esc_js($api_key); ?>'
                },
                body: JSON.stringify({
                    email: email,
                    name: name,
                    source: 'wordpress'
                })
            })
            .then(response => response.json())
            .then(data => {
                var messageDiv = document.getElementById('fikiri-form-message');
                if (data.success) {
                    messageDiv.innerHTML = '<p style="color: green;">Thank you! We\'ll be in touch soon.</p>';
                    document.getElementById('fikiri-lead-form').reset();
                } else {
                    messageDiv.innerHTML = '<p style="color: red;">Error: ' + (data.error || 'Unknown error') + '</p>';
                }
            })
            .catch(error => {
                document.getElementById('fikiri-form-message').innerHTML = '<p style="color: red;">Error submitting form.</p>';
            });
        });
    </script>
    <?php
    return ob_get_clean();
}
add_shortcode('fikiri_lead_capture', 'fikiri_lead_capture_shortcode');

// Admin settings page (optional)
function fikiri_settings_page() {
    ?>
    <div class="wrap">
        <h1>Fikiri Settings</h1>
        <form method="post" action="options.php">
            <?php settings_fields('fikiri_settings'); ?>
            <?php do_settings_sections('fikiri_settings'); ?>
            <table class="form-table">
                <tr>
                    <th scope="row">API Key</th>
                    <td>
                        <input type="text" name="fikiri_api_key" value="<?php echo esc_attr(get_option('fikiri_api_key')); ?>" class="regular-text" />
                        <p class="description">Get your API key from the Fikiri dashboard.</p>
                    </td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}

function fikiri_add_settings_page() {
    add_options_page('Fikiri Settings', 'Fikiri', 'manage_options', 'fikiri-settings', 'fikiri_settings_page');
}
add_action('admin_menu', 'fikiri_add_settings_page');

function fikiri_register_settings() {
    register_setting('fikiri_settings', 'fikiri_api_key');
}
add_action('admin_init', 'fikiri_register_settings');
