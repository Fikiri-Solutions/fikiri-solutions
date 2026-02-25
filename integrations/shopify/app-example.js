/**
 * Shopify App Example with Fikiri Integration
 * 
 * This example shows how to integrate Fikiri into a Shopify app
 * to sync customers, orders, and handle webhooks.
 */

import '@shopify/shopify-app/remix';
import { authenticate } from '@shopify/shopify-app/remix/server';
import { DeliveryMethod } from '@shopify/shopify-app/remix/server';

// Fikiri API configuration
const FIKIRI_API_URL = 'https://api.fikirisolutions.com';
const FIKIRI_API_KEY = process.env.FIKIRI_API_KEY;

/**
 * Webhook: Customer Created
 * Sync new Shopify customers to Fikiri CRM
 */
export const webhooks = {
  CUSTOMERS_CREATE: {
    deliveryMethod: DeliveryMethod.Http,
    callbackUrl: '/api/webhooks/shopify/customers/create',
    callback: async (topic, shop, body, webhookId) => {
      console.log(`[Fikiri] Processing customer create webhook for shop: ${shop}`);
      
      try {
        // Forward customer to Fikiri
        const response = await fetch(`${FIKIRI_API_URL}/api/webhooks/leads/capture`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': FIKIRI_API_KEY
          },
          body: JSON.stringify({
            email: body.email,
            name: `${body.first_name || ''} ${body.last_name || ''}`.trim(),
            phone: body.phone,
            source: 'shopify_customer',
            metadata: {
              shop_domain: shop,
              shopify_customer_id: body.id,
              customer_tags: body.tags,
              total_orders: body.orders_count || 0,
              total_spent: body.total_spent || '0.00',
              accepts_marketing: body.accepts_marketing,
              created_at: body.created_at
            }
          })
        });
        
        const result = await response.json();
        
        if (result.success) {
          console.log(`[Fikiri] Customer synced successfully: ${body.email} (Lead ID: ${result.lead_id})`);
        } else {
          console.error(`[Fikiri] Failed to sync customer: ${result.error}`);
        }
      } catch (error) {
        console.error(`[Fikiri] Error syncing customer: ${error.message}`);
      }
    }
  },
  
  /**
   * Webhook: Order Created
   * Create lead from new orders
   */
  ORDERS_CREATE: {
    deliveryMethod: DeliveryMethod.Http,
    callbackUrl: '/api/webhooks/shopify/orders/create',
    callback: async (topic, shop, body, webhookId) => {
      console.log(`[Fikiri] Processing order create webhook for shop: ${shop}`);
      
      try {
        const customer = body.customer;
        const order = body;
        
        // Create/update lead in Fikiri
        const response = await fetch(`${FIKIRI_API_URL}/api/webhooks/leads/capture`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': FIKIRI_API_KEY
          },
          body: JSON.stringify({
            email: customer.email || order.email,
            name: customer ? `${customer.first_name || ''} ${customer.last_name || ''}`.trim() : order.billing_address?.name,
            phone: customer?.phone || order.billing_address?.phone,
            source: 'shopify_order',
            metadata: {
              shop_domain: shop,
              shopify_order_id: order.id,
              shopify_order_number: order.order_number,
              shopify_customer_id: customer?.id,
              order_total: order.total_price,
              order_currency: order.currency,
              order_status: order.financial_status,
              order_items: order.line_items.map(item => ({
                product_id: item.product_id,
                variant_id: item.variant_id,
                title: item.title,
                quantity: item.quantity,
                price: item.price
              })),
              shipping_address: order.shipping_address,
              billing_address: order.billing_address,
              created_at: order.created_at
            }
          })
        });
        
        const result = await response.json();
        
        if (result.success) {
          console.log(`[Fikiri] Order synced successfully: Order #${order.order_number} (Lead ID: ${result.lead_id})`);
        } else {
          console.error(`[Fikiri] Failed to sync order: ${result.error}`);
        }
      } catch (error) {
        console.error(`[Fikiri] Error syncing order: ${error.message}`);
      }
    }
  },
  
  /**
   * Webhook: Cart Abandoned (via third-party app or custom tracking)
   * Capture leads from abandoned carts
   */
  CART_ABANDONED: {
    deliveryMethod: DeliveryMethod.Http,
    callbackUrl: '/api/webhooks/shopify/cart/abandoned',
    callback: async (topic, shop, body, webhookId) => {
      console.log(`[Fikiri] Processing abandoned cart for shop: ${shop}`);
      
      try {
        const response = await fetch(`${FIKIRI_API_URL}/api/webhooks/leads/capture`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': FIKIRI_API_KEY
          },
          body: JSON.stringify({
            email: body.email,
            name: body.customer_name,
            source: 'shopify_abandoned_cart',
            metadata: {
              shop_domain: shop,
              cart_token: body.cart_token,
              cart_value: body.total_price,
              cart_items: body.line_items,
              abandoned_at: body.abandoned_at
            }
          })
        });
        
        const result = await response.json();
        console.log(`[Fikiri] Abandoned cart captured: ${body.email} (Lead ID: ${result.lead_id})`);
      } catch (error) {
        console.error(`[Fikiri] Error capturing abandoned cart: ${error.message}`);
      }
    }
  }
};

/**
 * App Route: Sync All Customers
 * Manually sync all Shopify customers to Fikiri
 */
export async function syncCustomers(request) {
  const { admin } = await authenticate.admin(request);
  
  try {
    const customers = await admin.rest.resources.Customer.all({
      session: admin.session
    });
    
    let synced = 0;
    let failed = 0;
    
    for (const customer of customers.data) {
      try {
        const response = await fetch(`${FIKIRI_API_URL}/api/webhooks/leads/capture`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': FIKIRI_API_KEY
          },
          body: JSON.stringify({
            email: customer.email,
            name: `${customer.first_name || ''} ${customer.last_name || ''}`.trim(),
            phone: customer.phone,
            source: 'shopify_customer_sync',
            metadata: {
              shop_domain: admin.session.shop,
              shopify_customer_id: customer.id,
              total_orders: customer.orders_count,
              total_spent: customer.total_spent
            }
          })
        });
        
        const result = await response.json();
        if (result.success) {
          synced++;
        } else {
          failed++;
        }
      } catch (error) {
        failed++;
        console.error(`Failed to sync customer ${customer.email}: ${error.message}`);
      }
    }
    
    return {
      success: true,
      synced,
      failed,
      total: customers.data.length
    };
  } catch (error) {
    console.error(`Error syncing customers: ${error.message}`);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * App Route: Initialize Fikiri SDK in Storefront
 * Add script tag to storefront
 */
export async function initializeStorefront(request) {
  const { admin } = await authenticate.admin(request);
  
  try {
    // Add Fikiri SDK script tag
    const scriptTag = await admin.rest.resources.ScriptTag.create({
      session: admin.session,
      event: 'onload',
      src: 'https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js',
      display_scope: 'online_store'
    });
    
    return {
      success: true,
      script_tag_id: scriptTag.id
    };
  } catch (error) {
    console.error(`Error adding script tag: ${error.message}`);
    return {
      success: false,
      error: error.message
    };
  }
}
