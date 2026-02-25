# Fikiri Chatbot Demo

**Live demo of Fikiri's AI-powered chatbot**

---

## 🚀 Quick Start

### Option 1: Open Demo HTML File

1. **Start your Flask server:**
   ```bash
   python app.py
   ```

2. **Open the demo:**
   - Navigate to `http://localhost:5000/demo/chatbot-demo.html`
   - Or open `demo/chatbot-demo.html` directly in your browser

3. **Enter your API key:**
   - Get your API key from the Fikiri dashboard
   - Paste it in the setup section
   - Click "Initialize Chatbot"

4. **Start chatting!**

---

## 📋 Requirements

- Flask server running (`python app.py`)
- Valid Fikiri API key
- Modern browser (Chrome, Firefox, Safari, Edge)

---

## 🎯 Features Demonstrated

- ✅ **AI-Powered Responses** - Uses FAQ + Knowledge Base
- ✅ **Multi-Turn Conversations** - Maintains context
- ✅ **Real-Time Chat** - Instant responses
- ✅ **Lead Capture** - Integrated lead collection
- ✅ **Source Attribution** - Shows where answers come from
- ✅ **Error Handling** - Graceful error messages

---

## 🔧 Customization

### Change API URL

If your API is hosted elsewhere, edit the demo:

```javascript
Fikiri.init({
    apiKey: apiKey,
    apiUrl: 'https://your-api-url.com', // Change this
    features: ['chatbot', 'leadCapture'],
    debug: true
});
```

### Customize Styling

Edit the `<style>` section in `chatbot-demo.html` to match your brand colors.

---

## 📝 Example Questions to Try

- "What are your business hours?"
- "How do I get started?"
- "Tell me about your pricing"
- "What services do you offer?"
- "How can I contact support?"

---

## 🐛 Troubleshooting

### "API key is required"
- Make sure you've entered your API key
- API key should start with `fik_`

### "Network error"
- Check that Flask server is running
- Verify API URL is correct
- Check browser console for CORS errors

### "Chatbot not responding"
- Check browser console for errors
- Verify API key has `chatbot:query` scope
- Check Flask server logs

---

## 🚀 Next Steps

1. **Deploy to production** - Host on your domain
2. **Add to your website** - Use the Install page (`/install`)
3. **Customize styling** - Match your brand
4. **Add more features** - Lead capture, forms, etc.

---

*Last updated: February 2026*
