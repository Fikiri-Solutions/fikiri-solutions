<?php
/**
 * Plugin Name: Fikiri Integration
 * Plugin URI: https://fikirisolutions.com
 * Description: Integrate Fikiri chatbot, lead capture, and CRM features into your WordPress site
 * Version: 1.0.0
 * Author: Fikiri Solutions
 * Author URI: https://fikirisolutions.com
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: fikiri
 */

// Exit if accessed directly
if (!defined('ABSPATH')) {
    exit;
}

// Define plugin constants
define('FIKIRI_PLUGIN_VERSION', '1.0.0');
define('FIKIRI_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('FIKIRI_PLUGIN_URL', plugin_dir_url(__FILE__));
define('FIKIRI_API_URL', 'https://api.fikirisolutions.com');

/**
 * Main Fikiri Plugin Class
 */
class Fikiri_Plugin {
    
    private static $instance = null;
    
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('admin_init', array($this, 'register_settings'));
        add_action('wp_footer', array($this, 'enqueue_sdk'));
        add_action('wp_enqueue_scripts', array($this, 'enqueue_styles'));
        
        // Shortcodes
        add_shortcode('fikiri_chatbot', array($this, 'chatbot_shortcode'));
        add_shortcode('fikiri_lead_capture', array($this, 'lead_capture_shortcode'));
        add_shortcode('fikiri_contact_form', array($this, 'contact_form_shortcode'));
        
        // Gutenberg block registration
        add_action('init', array($this, 'register_gutenberg_blocks'));
    }
    
    /**
     * Add admin menu
     */
    public function add_admin_menu() {
        add_options_page(
            'Fikiri Settings',
            'Fikiri',
            'manage_options',
            'fikiri-settings',
            array($this, 'render_settings_page')
        );
    }
    
    /**
     * Register settings
     */
    public function register_settings() {
        register_setting('fikiri_settings', 'fikiri_api_key', array(
            'type' => 'string',
            'sanitize_callback' => 'sanitize_text_field',
            'default' => ''
        ));
        
        register_setting('fikiri_settings', 'fikiri_tenant_id', array(
            'type' => 'string',
            'sanitize_callback' => 'sanitize_text_field',
            'default' => ''
        ));
        
        register_setting('fikiri_settings', 'fikiri_chatbot_enabled', array(
            'type' => 'boolean',
            'default' => true
        ));
        
        register_setting('fikiri_settings', 'fikiri_chatbot_theme', array(
            'type' => 'string',
            'default' => 'light'
        ));
        
        register_setting('fikiri_settings', 'fikiri_chatbot_position', array(
            'type' => 'string',
            'default' => 'bottom-right'
        ));
        
        register_setting('fikiri_settings', 'fikiri_chatbot_title', array(
            'type' => 'string',
            'default' => 'Chat with us'
        ));
    }
    
    /**
     * Render settings page
     */
    public function render_settings_page() {
        if (!current_user_can('manage_options')) {
            return;
        }
        
        ?>
        <div class="wrap">
            <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
            <form action="options.php" method="post">
                <?php
                settings_fields('fikiri_settings');
                do_settings_sections('fikiri_settings');
                ?>
                <table class="form-table">
                    <tr>
                        <th scope="row">
                            <label for="fikiri_api_key">API Key</label>
                        </th>
                        <td>
                            <input 
                                type="text" 
                                id="fikiri_api_key" 
                                name="fikiri_api_key" 
                                value="<?php echo esc_attr(get_option('fikiri_api_key')); ?>" 
                                class="regular-text"
                                placeholder="fik_your_api_key_here"
                            />
                            <p class="description">
                                Get your API key from the <a href="https://app.fikirisolutions.com/settings/api-keys" target="_blank">Fikiri dashboard</a>.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">
                            <label for="fikiri_tenant_id">Tenant ID (Optional)</label>
                        </th>
                        <td>
                            <input 
                                type="text" 
                                id="fikiri_tenant_id" 
                                name="fikiri_tenant_id" 
                                value="<?php echo esc_attr(get_option('fikiri_tenant_id')); ?>" 
                                class="regular-text"
                            />
                            <p class="description">
                                Optional tenant identifier for multi-tenant setups.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Chatbot Settings</th>
                        <td>
                            <fieldset>
                                <label>
                                    <input 
                                        type="checkbox" 
                                        name="fikiri_chatbot_enabled" 
                                        value="1" 
                                        <?php checked(get_option('fikiri_chatbot_enabled'), 1); ?>
                                    />
                                    Enable chatbot widget
                                </label>
                            </fieldset>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">
                            <label for="fikiri_chatbot_theme">Chatbot Theme</label>
                        </th>
                        <td>
                            <select id="fikiri_chatbot_theme" name="fikiri_chatbot_theme">
                                <option value="light" <?php selected(get_option('fikiri_chatbot_theme'), 'light'); ?>>Light</option>
                                <option value="dark" <?php selected(get_option('fikiri_chatbot_theme'), 'dark'); ?>>Dark</option>
                            </select>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">
                            <label for="fikiri_chatbot_position">Chatbot Position</label>
                        </th>
                        <td>
                            <select id="fikiri_chatbot_position" name="fikiri_chatbot_position">
                                <option value="bottom-right" <?php selected(get_option('fikiri_chatbot_position'), 'bottom-right'); ?>>Bottom Right</option>
                                <option value="bottom-left" <?php selected(get_option('fikiri_chatbot_position'), 'bottom-left'); ?>>Bottom Left</option>
                                <option value="top-right" <?php selected(get_option('fikiri_chatbot_position'), 'top-right'); ?>>Top Right</option>
                                <option value="top-left" <?php selected(get_option('fikiri_chatbot_position'), 'top-left'); ?>>Top Left</option>
                            </select>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">
                            <label for="fikiri_chatbot_title">Chatbot Title</label>
                        </th>
                        <td>
                            <input 
                                type="text" 
                                id="fikiri_chatbot_title" 
                                name="fikiri_chatbot_title" 
                                value="<?php echo esc_attr(get_option('fikiri_chatbot_title', 'Chat with us')); ?>" 
                                class="regular-text"
                            />
                        </td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>
            
            <hr>
            
            <h2>Shortcodes</h2>
            <p>Use these shortcodes to add Fikiri features to your pages:</p>
            <ul>
                <li><code>[fikiri_chatbot]</code> - Display chatbot widget</li>
                <li><code>[fikiri_lead_capture]</code> - Display lead capture form</li>
                <li><code>[fikiri_contact_form]</code> - Display contact form</li>
            </ul>
            
            <h3>Shortcode Parameters</h3>
            <p><strong>Chatbot:</strong></p>
            <ul>
                <li><code>theme</code> - "light" or "dark" (default: "light")</li>
                <li><code>position</code> - "bottom-right", "bottom-left", "top-right", "top-left" (default: "bottom-right")</li>
                <li><code>title</code> - Widget title text</li>
            </ul>
            <p><strong>Lead Capture:</strong></p>
            <ul>
                <li><code>fields</code> - Comma-separated fields: "email", "name", "phone" (default: "email,name")</li>
                <li><code>title</code> - Form title</li>
            </ul>
        </div>
        <?php
    }
    
    /**
     * Enqueue Fikiri SDK
     */
    public function enqueue_sdk() {
        $api_key = get_option('fikiri_api_key');
        if (empty($api_key)) {
            return;
        }
        
        $chatbot_enabled = get_option('fikiri_chatbot_enabled', true);
        $tenant_id = get_option('fikiri_tenant_id', '');
        
        ?>
        <script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
        <script>
            (function() {
                var config = {
                    apiKey: <?php echo json_encode($api_key); ?>,
                    features: ['chatbot', 'leadCapture']
                };
                
                <?php if (!empty($tenant_id)): ?>
                config.tenantId = <?php echo json_encode($tenant_id); ?>;
                <?php endif; ?>
                
                Fikiri.init(config);
                
                <?php if ($chatbot_enabled): ?>
                // Show chatbot after page load
                window.addEventListener('load', function() {
                    Fikiri.Chatbot.show({
                        theme: <?php echo json_encode(get_option('fikiri_chatbot_theme', 'light')); ?>,
                        position: <?php echo json_encode(get_option('fikiri_chatbot_position', 'bottom-right')); ?>,
                        title: <?php echo json_encode(get_option('fikiri_chatbot_title', 'Chat with us')); ?>
                    });
                });
                <?php endif; ?>
            })();
        </script>
        <?php
    }
    
    /**
     * Enqueue styles
     */
    public function enqueue_styles() {
        // Optional: Add custom styles if needed
    }
    
    /**
     * Chatbot shortcode
     */
    public function chatbot_shortcode($atts) {
        $api_key = get_option('fikiri_api_key');
        if (empty($api_key)) {
            return '<p style="color: red;">Fikiri API key not configured. Please configure it in Settings → Fikiri.</p>';
        }
        
        $atts = shortcode_atts(array(
            'theme' => get_option('fikiri_chatbot_theme', 'light'),
            'position' => get_option('fikiri_chatbot_position', 'bottom-right'),
            'title' => get_option('fikiri_chatbot_title', 'Chat with us')
        ), $atts);
        
        ob_start();
        ?>
        <script>
            if (typeof Fikiri === 'undefined') {
                var script = document.createElement('script');
                script.src = 'https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js';
                script.onload = function() {
                    Fikiri.init({
                        apiKey: <?php echo json_encode($api_key); ?>
                    });
                    Fikiri.Chatbot.show({
                        theme: <?php echo json_encode($atts['theme']); ?>,
                        position: <?php echo json_encode($atts['position']); ?>,
                        title: <?php echo json_encode($atts['title']); ?>
                    });
                };
                document.head.appendChild(script);
            } else {
                Fikiri.Chatbot.show({
                    theme: <?php echo json_encode($atts['theme']); ?>,
                    position: <?php echo json_encode($atts['position']); ?>,
                    title: <?php echo json_encode($atts['title']); ?>
                });
            }
        </script>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Lead capture shortcode
     */
    public function lead_capture_shortcode($atts) {
        $api_key = get_option('fikiri_api_key');
        if (empty($api_key)) {
            return '<p style="color: red;">Fikiri API key not configured.</p>';
        }
        
        $atts = shortcode_atts(array(
            'fields' => 'email,name',
            'title' => 'Get in Touch'
        ), $atts);
        
        $fields_array = array_map('trim', explode(',', $atts['fields']));
        $has_name = in_array('name', $fields_array);
        $has_phone = in_array('phone', $fields_array);
        
        ob_start();
        ?>
        <div class="fikiri-lead-capture-form" style="max-width: 400px; margin: 20px 0;">
            <h3><?php echo esc_html($atts['title']); ?></h3>
            <form id="fikiri-lead-form-<?php echo uniqid(); ?>">
                <?php if ($has_name): ?>
                <p>
                    <label>Name:</label><br>
                    <input type="text" name="name" required style="width: 100%; padding: 8px; box-sizing: border-box;">
                </p>
                <?php endif; ?>
                <p>
                    <label>Email:</label><br>
                    <input type="email" name="email" required style="width: 100%; padding: 8px; box-sizing: border-box;">
                </p>
                <?php if ($has_phone): ?>
                <p>
                    <label>Phone:</label><br>
                    <input type="tel" name="phone" style="width: 100%; padding: 8px; box-sizing: border-box;">
                </p>
                <?php endif; ?>
                <p>
                    <button type="submit" style="padding: 10px 20px; background: #0f766e; color: white; border: none; cursor: pointer; border-radius: 4px;">
                        Submit
                    </button>
                </p>
                <div class="fikiri-form-message" style="margin-top: 10px;"></div>
            </form>
        </div>
        <script>
            (function() {
                var form = document.getElementById('fikiri-lead-form-<?php echo uniqid(); ?>');
                var messageDiv = form.querySelector('.fikiri-form-message');
                
                form.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    var formData = new FormData(form);
                    var data = {
                        email: formData.get('email'),
                        name: formData.get('name') || '',
                        phone: formData.get('phone') || '',
                        source: 'wordpress'
                    };
                    
                    messageDiv.innerHTML = '<p>Submitting...</p>';
                    
                    fetch('<?php echo esc_url(FIKIRI_API_URL); ?>/api/webhooks/leads/capture', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': <?php echo json_encode($api_key); ?>
                        },
                        body: JSON.stringify(data)
                    })
                    .then(function(response) { return response.json(); })
                    .then(function(result) {
                        if (result.success) {
                            messageDiv.innerHTML = '<p style="color: green;">Thank you! We\'ll be in touch soon.</p>';
                            form.reset();
                        } else {
                            messageDiv.innerHTML = '<p style="color: red;">Error: ' + (result.error || 'Unknown error') + '</p>';
                        }
                    })
                    .catch(function(error) {
                        messageDiv.innerHTML = '<p style="color: red;">Error submitting form. Please try again.</p>';
                    });
                });
            })();
        </script>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Contact form shortcode
     */
    public function contact_form_shortcode($atts) {
        return $this->lead_capture_shortcode(array_merge($atts, array('fields' => 'email,name,phone')));
    }
    
    /**
     * Register Gutenberg blocks
     */
    public function register_gutenberg_blocks() {
        if (!function_exists('register_block_type')) {
            return; // Gutenberg not available
        }
        
        // Register chatbot block
        register_block_type('fikiri/chatbot', array(
            'editor_script' => 'fikiri-block-editor',
            'render_callback' => array($this, 'chatbot_shortcode'),
            'attributes' => array(
                'theme' => array('type' => 'string', 'default' => 'light'),
                'position' => array('type' => 'string', 'default' => 'bottom-right'),
                'title' => array('type' => 'string', 'default' => 'Chat with us')
            )
        ));
        
        // Register lead capture block
        register_block_type('fikiri/lead-capture', array(
            'editor_script' => 'fikiri-block-editor',
            'render_callback' => array($this, 'lead_capture_shortcode'),
            'attributes' => array(
                'fields' => array('type' => 'string', 'default' => 'email,name'),
                'title' => array('type' => 'string', 'default' => 'Get in Touch')
            )
        ));
    }
}

// Initialize plugin
function fikiri_plugin_init() {
    return Fikiri_Plugin::get_instance();
}

// Start the plugin
add_action('plugins_loaded', 'fikiri_plugin_init');
