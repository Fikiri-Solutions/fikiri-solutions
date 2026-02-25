# Fikiri SquareSpace Integration

Add Fikiri chatbot and lead capture features to your SquareSpace site.

## Installation

### Method 1: Code Block (Easiest)

1. Edit your SquareSpace page
2. Add a **Code** block
3. Paste the code below (replace `YOUR_API_KEY` with your actual API key):

```html
<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: 'YOUR_API_KEY',
    features: ['chatbot', 'leadCapture']
  });
  
  // Show chatbot
  Fikiri.Chatbot.show({
    theme: 'light',
    position: 'bottom-right',
    title: 'Chat with us'
  });
</script>
```

### Method 2: Site-Wide Integration

1. Go to **Settings** → **Advanced** → **Code Injection**
2. Add to **Footer**:

```html
<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({
    apiKey: 'YOUR_API_KEY',
    features: ['chatbot', 'leadCapture']
  });
  
  window.addEventListener('load', function() {
    Fikiri.Chatbot.show();
  });
</script>
```

### Method 3: Lead Capture Form

Add a **Code** block with:

```html
<div id="fikiri-lead-capture">
  <h3>Get in Touch</h3>
  <form id="fikiri-lead-form">
    <p>
      <label>Name:</label><br>
      <input type="text" name="name" required style="width: 100%; padding: 8px;">
    </p>
    <p>
      <label>Email:</label><br>
      <input type="email" name="email" required style="width: 100%; padding: 8px;">
    </p>
    <p>
      <button type="submit" style="padding: 10px 20px; background: #0f766e; color: white; border: none; cursor: pointer;">
        Submit
      </button>
    </p>
    <div id="fikiri-form-message"></div>
  </form>
</div>

<script src="https://cdn.fikirisolutions.com/sdk/v1/fikiri-sdk.js"></script>
<script>
  Fikiri.init({ apiKey: 'YOUR_API_KEY' });
  
  document.getElementById('fikiri-lead-form').addEventListener('submit', function(e) {
    e.preventDefault();
    var formData = new FormData(this);
    
    Fikiri.LeadCapture.capture({
      email: formData.get('email'),
      name: formData.get('name'),
      source: 'squarespace'
    }).then(function(result) {
      var msg = document.getElementById('fikiri-form-message');
      if (result.success) {
        msg.innerHTML = '<p style="color: green;">Thank you! We\'ll be in touch soon.</p>';
        this.reset();
      } else {
        msg.innerHTML = '<p style="color: red;">Error: ' + result.error + '</p>';
      }
    }.bind(this));
  });
</script>
```

## SquareSpace Block (Coming Soon)

A native SquareSpace block/widget is planned for easier drag-and-drop integration.

## Getting Your API Key

1. Log into [Fikiri dashboard](https://app.fikirisolutions.com)
2. Go to **Settings** → **API Keys**
3. Click **Create API Key**
4. Copy the key (starts with `fik_`)

## Customization

### Chatbot Theme
```javascript
Fikiri.Chatbot.show({
  theme: 'light',  // or 'dark'
  position: 'bottom-right',  // or 'bottom-left', 'top-right', 'top-left'
  title: 'Chat with us'
});
```

### Lead Capture Fields
```javascript
Fikiri.LeadCapture.capture({
  email: 'user@example.com',
  name: 'John Doe',
  phone: '+1-555-123-4567',  // optional
  source: 'squarespace'
});
```

## Support

For help, visit [Fikiri Support](https://fikirisolutions.com/support) or email support@fikirisolutions.com
