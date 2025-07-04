# 🔧 Troubleshooting Guide

## Gemini API Model Issues

### Error: "404 models/gemini-pro is not found"

**✅ Solution Applied:**
I've updated your configuration to use `models/gemini-1.5-flash` instead of `gemini-pro`.

**🔄 Alternative Models to Try:**
If you still encounter issues, try these models in order:

1. `models/gemini-1.5-flash` (fastest, recommended)
2. `models/gemini-1.5-pro` (more capable)
3. `gemini-1.5-flash` (without models/ prefix)
4. `gemini-1.5-pro` (without models/ prefix)

### How to Change the Model

**Option 1: Update config.py**
```python
# In config.py, change:
GEMINI_MODEL = "models/gemini-1.5-flash"
```

**Option 2: Test which models work**
```bash
# Run the test script to see available models
python test_gemini.py
```

**Option 3: Manual testing**
```python
import google.generativeai as genai
genai.configure(api_key="YOUR_API_KEY_HERE")

# List available models
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(model.name)
```

### Common Fixes

1. **API Key Issues**
   - Verify your key is correctly formatted and active
   - Enable Gemini API in Google Cloud Console
   - Check quota limits

2. **Model Name Issues**
   - Use full path: `models/gemini-1.5-flash`
   - Try different model versions
   - Check model availability in your region

3. **Installation Issues**
   ```bash
   pip install --upgrade google-generativeai
   pip install --upgrade langchain-google-genai
   ```

### Quick Test

Run this to verify your setup:
```python
from langchain_google_genai import ChatGoogleGenerativeAI
import os

os.environ["GOOGLE_API_KEY"] = "YOUR_API_KEY_HERE"
llm = ChatGoogleGenerativeAI(model="models/gemini-1.5-flash", temperature=0.1)
response = llm.invoke("Hello, respond with 'Working!' if you can see this.")
print(response.content)
```

### If Nothing Works

Try these fallback options:

1. **Use OpenAI instead**
   ```bash
   pip install langchain-openai
   # Update ticket_agent.py to use ChatOpenAI
   ```

2. **Use local models**
   ```bash
   pip install langchain-ollama
   # Use Ollama for local inference
   ```

3. **Use Anthropic Claude**
   ```bash
   pip install langchain-anthropic
   # Use Claude via Anthropic API
   ```

### Getting Help

- Check [Google AI Studio](https://aistudio.google.com/) for model availability
- Visit [Gemini API docs](https://ai.google.dev/docs) for latest updates
- Run `python test_gemini.py` to diagnose issues

---

**Your app should now work with the updated configuration!** 🚀 