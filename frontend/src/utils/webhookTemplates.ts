/**
 * Webhook Templates for Common Services
 * Pre-configured payload structures for popular webhook destinations
 */

export interface WebhookTemplate {
  id: string
  name: string
  description: string
  icon: string
  defaultPayload: Record<string, any>
  fields: WebhookField[]
  exampleUrl?: string
}

export interface WebhookField {
  key: string
  label: string
  type: 'text' | 'number' | 'boolean' | 'select' | 'email' | 'url'
  required?: boolean
  placeholder?: string
  helper?: string
  options?: { value: string; label: string }[]
  defaultValue?: any
}

export const webhookTemplates: WebhookTemplate[] = [
  {
    id: 'slack',
    name: 'Slack',
    description: 'Get instant notifications in your Slack channel when new leads come in',
    icon: '💬',
    exampleUrl: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
    defaultPayload: {
      text: 'New automation triggered',
      blocks: [
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: '*New Lead Created*\nEmail: {sender_email}\nSubject: {subject}'
          }
        }
      ]
    },
    fields: [
      {
        key: 'text',
        label: 'Message Text',
        type: 'text',
        required: true,
        placeholder: 'Notification message',
        helper: 'Main message text for Slack notification'
      },
      {
        key: 'channel',
        label: 'Channel',
        type: 'text',
        placeholder: '#general',
        helper: 'Optional: Override default channel'
      }
    ]
  },
  {
    id: 'google_sheets',
    name: 'Google Sheets',
    description: 'Automatically add new leads to your spreadsheet - perfect for tracking and sharing with your team',
    icon: '📊',
    exampleUrl: 'https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec',
    defaultPayload: {
      action: 'append',
      sheet: 'Sheet1',
      values: [
        ['{sender_email}', '{subject}', '{timestamp}']
      ]
    },
    fields: [
      {
        key: 'sheet',
        label: 'Sheet Name',
        type: 'text',
        defaultValue: 'Sheet1',
        placeholder: 'Sheet1',
        helper: 'Name of the sheet tab'
      },
      {
        key: 'action',
        label: 'Action',
        type: 'select',
        defaultValue: 'append',
        options: [
          { value: 'append', label: 'Append Row' },
          { value: 'update', label: 'Update Row' }
        ]
      }
    ]
  },
  {
    id: 'zapier',
    name: 'Zapier',
    description: 'Connect Fikiri to 5,000+ apps through Zapier - automate your entire workflow',
    icon: '⚡',
    exampleUrl: 'https://hooks.zapier.com/hooks/catch/YOUR/WEBHOOK/ID',
    defaultPayload: {
      event: '{event_type}',
      data: {
        email: '{sender_email}',
        subject: '{subject}',
        timestamp: '{timestamp}',
        user_id: '{user_id}'
      }
    },
    fields: [
      {
        key: 'event',
        label: 'Event Name',
        type: 'text',
        required: true,
        placeholder: 'new_lead',
        helper: 'Event identifier for Zapier trigger'
      }
    ]
  },
  {
    id: 'airtable',
    name: 'Airtable',
    description: 'Add new leads directly to your Airtable database - keep everything organized in one place',
    icon: '🗂️',
    exampleUrl: 'https://api.airtable.com/v0/YOUR_BASE/YOUR_TABLE',
    defaultPayload: {
      fields: {
        'Email': '{sender_email}',
        'Subject': '{subject}',
        'Date': '{timestamp}',
        'Status': 'New'
      }
    },
    fields: [
      {
        key: 'table',
        label: 'Table Name',
        type: 'text',
        required: true,
        placeholder: 'Leads',
        helper: 'Airtable table name'
      }
    ]
  },
  {
    id: 'discord',
    name: 'Discord',
    description: 'Get notified in your Discord server when important events happen',
    icon: '🎮',
    exampleUrl: 'https://discord.com/api/webhooks/YOUR/WEBHOOK/URL',
    defaultPayload: {
      content: 'New automation triggered',
      embeds: [
        {
          title: 'New Lead',
          description: 'Email: {sender_email}\nSubject: {subject}',
          color: 0x00ff00,
          timestamp: '{timestamp}'
        }
      ]
    },
    fields: [
      {
        key: 'content',
        label: 'Message Content',
        type: 'text',
        placeholder: 'Notification message',
        helper: 'Main message text'
      },
      {
        key: 'username',
        label: 'Bot Username',
        type: 'text',
        placeholder: 'Fikiri Bot',
        helper: 'Optional: Custom bot username'
      }
    ]
  },
  {
    id: 'make_com',
    name: 'Make.com (Integromat)',
    description: 'Connect to Make.com to build powerful automated workflows between apps',
    icon: '🔗',
    exampleUrl: 'https://hook.integromat.com/YOUR_WEBHOOK_ID',
    defaultPayload: {
      event: '{event_type}',
      payload: {
        email: '{sender_email}',
        subject: '{subject}',
        timestamp: '{timestamp}'
      }
    },
    fields: [
      {
        key: 'event',
        label: 'Event Type',
        type: 'text',
        required: true,
        placeholder: 'email_received',
        helper: 'Event type identifier'
      }
    ]
  },
  {
    id: 'custom',
    name: 'Custom Webhook',
    description: 'Connect to your own system or app - we\'ll help you set it up',
    icon: '🔧',
    defaultPayload: {
      event: '{event_type}',
      data: {
        email: '{sender_email}',
        subject: '{subject}',
        timestamp: '{timestamp}'
      }
    },
    fields: []
  }
]

/**
 * Available variables that can be used in webhook payloads
 */
export const webhookVariables = [
  { key: '{user_id}', label: 'User ID', description: 'Current user ID' },
  { key: '{timestamp}', label: 'Timestamp', description: 'ISO timestamp of the event' },
  { key: '{event_type}', label: 'Event Type', description: 'Type of automation trigger' },
  { key: '{sender_email}', label: 'Sender Email', description: 'Email address of the sender (email triggers)' },
  { key: '{subject}', label: 'Email Subject', description: 'Subject line of the email (email triggers)' },
  { key: '{email_body}', label: 'Email Body', description: 'Body text of the email (email triggers)' },
  { key: '{lead_id}', label: 'Lead ID', description: 'ID of the lead (lead triggers)' },
  { key: '{lead_name}', label: 'Lead Name', description: 'Name of the lead (lead triggers)' },
  { key: '{lead_email}', label: 'Lead Email', description: 'Email of the lead (lead triggers)' },
  { key: '{old_stage}', label: 'Old Stage', description: 'Previous pipeline stage (stage change triggers)' },
  { key: '{new_stage}', label: 'New Stage', description: 'New pipeline stage (stage change triggers)' }
]

/**
 * Replace variables in a payload with actual values
 */
export function replaceVariables(
  payload: any,
  triggerData: Record<string, any> = {},
  userId?: number
): any {
  if (typeof payload === 'string') {
    let result = payload
    result = result.replace(/{user_id}/g, String(userId || ''))
    result = result.replace(/{timestamp}/g, new Date().toISOString())
    result = result.replace(/{event_type}/g, triggerData.event_type || 'automation_triggered')
    result = result.replace(/{sender_email}/g, triggerData.sender_email || triggerData.email || '')
    result = result.replace(/{subject}/g, triggerData.subject || '')
    result = result.replace(/{email_body}/g, triggerData.text || triggerData.body || '')
    result = result.replace(/{lead_id}/g, String(triggerData.lead_id || ''))
    result = result.replace(/{lead_name}/g, triggerData.lead_name || triggerData.name || '')
    result = result.replace(/{lead_email}/g, triggerData.lead_email || triggerData.email || '')
    result = result.replace(/{old_stage}/g, triggerData.old_stage || '')
    result = result.replace(/{new_stage}/g, triggerData.new_stage || '')
    return result
  }
  
  if (Array.isArray(payload)) {
    return payload.map(item => replaceVariables(item, triggerData, userId))
  }
  
  if (payload && typeof payload === 'object') {
    const result: Record<string, any> = {}
    for (const [key, value] of Object.entries(payload)) {
      result[key] = replaceVariables(value, triggerData, userId)
    }
    return result
  }
  
  return payload
}

