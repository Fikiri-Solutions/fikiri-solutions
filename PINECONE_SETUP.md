# Pinecone Integration Setup

## Quick Setup

Pinecone is now **optional** - the system works with local storage by default.

### To Use Pinecone:

1. **Install Pinecone SDK:**
   ```bash
   pip install pinecone-client
   ```

2. **Set Environment Variables:**
   ```bash
   export PINECONE_API_KEY="your-api-key-here"
   export PINECONE_INDEX_NAME="fikiri-vectors"  # Optional, defaults to "fikiri-vectors"
   ```

3. **Restart Backend:**
   - The system will automatically detect Pinecone and use it
   - If Pinecone is not configured, it falls back to local storage

### How It Works:

- **With Pinecone:** Vectors stored in Pinecone cloud, managed infrastructure
- **Without Pinecone:** Vectors stored locally in `data/vector_db.pkl`

### Benefits of Pinecone:

- ✅ Managed infrastructure (no server management)
- ✅ Scales to millions of vectors
- ✅ Fast search performance
- ✅ Built-in redundancy

### When to Use Local Storage:

- ✅ Small to medium datasets (< 100K vectors)
- ✅ Want zero external dependencies
- ✅ Cost-sensitive (Pinecone has usage limits on free tier)

The code automatically chooses the best option based on your configuration!

