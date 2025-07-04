# 📚 Knowledge Base Setup Guide

## Overview

The AI Support Agent includes a powerful knowledge base system that uses Retrieval-Augmented Generation (RAG) to provide intelligent responses based on your documentation. This guide will walk you through setting up and managing your knowledge base.

---

## 🗂️ Knowledge Files Structure

### Where to Place Knowledge Files

All knowledge documents should be placed in the `Knowledge/` directory:

```
AI support agent/
├── Knowledge/
│   ├── User_Guide.docx           # ✅ Main user documentation
│   ├── API_Documentation.docx    # ✅ API reference
│   ├── Troubleshooting_Guide.docx # ✅ Common issues and solutions
│   ├── Feature_Overview.docx     # ✅ Feature descriptions
│   └── (your additional documents...)
├── src/
├── streamlit_app.py
└── README.md
```

### Supported File Formats

- **Word Documents (.docx)**: Recommended format
- **PDF Files (.pdf)**: Supported (requires additional processing)
- **Text Files (.txt)**: Basic support
- **Markdown Files (.md)**: Supported

### Sample Knowledge Base

The project includes a complete sample knowledge base for "TaskFlow Pro" - a fictional SaaS project management platform. These files demonstrate best practices:

1. **User_Guide.docx**: Getting started, features, pricing plans
2. **API_Documentation.docx**: REST API endpoints, authentication, examples
3. **Troubleshooting_Guide.docx**: Common issues and step-by-step solutions
4. **Feature_Overview.docx**: Detailed feature descriptions and capabilities

---

## 🚀 Building the Knowledge Base

### Method 1: Using the Streamlit Interface (Recommended)

1. **Start the Application**:
   ```bash
   streamlit run streamlit_app.py --server.port 8502
   ```

2. **Navigate to Knowledge Base**:
   - Go to http://localhost:8502
   - Enter your Gemini API key in the sidebar
   - Select "Knowledge Base" from the navigation

3. **Build the Knowledge Base**:
   - The interface will automatically detect `.docx` files in the `Knowledge/` directory
   - Click the build button to create the vector index
   - Choose between "Vector-based" or "Text-search" methods

### Method 2: Using Build Scripts

#### Vector-Based Knowledge Base (Recommended)
```bash
python build_knowledge_base_robust.py
```

Features:
- Uses sentence transformers for embeddings
- FAISS vector index for fast similarity search
- Supports complex queries and semantic search

#### Text-Based Knowledge Base (Faster Setup)
```bash
python build_text_search_knowledge.py
```

Features:
- Word and phrase indexing
- Category-based organization
- Faster to build, good for exact matches

#### Lightweight Knowledge Base
```bash
python build_knowledge_base.py
```

Features:
- Simple implementation
- Good for small knowledge bases
- Quick setup and testing

### Method 3: Using the Knowledge API

1. **Start the API Server**:
   ```bash
   cd src
   python knowledge_api.py
   ```

2. **Build via API**:
   ```bash
   curl -X POST "http://localhost:8000/build" \
        -H "Content-Type: application/json" \
        -d '{"build_type": "vector", "force": true}'
   ```

---

## 🔧 Configuration Options

### Environment Variables

Add these to your `.env` file:

```bash
# Knowledge Base Configuration
KNOWLEDGE_BASE_PATH=./Knowledge
KNOWLEDGE_BUILD_TYPE=vector
MAX_DOCUMENTS=100
CHUNK_SIZE=1000

# Vector Store Configuration
VECTOR_STORE_TYPE=faiss
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Build Types Comparison

| Feature | Vector-Based | Text-Based | Lightweight |
|---------|-------------|------------|-------------|
| **Setup Time** | Medium | Fast | Very Fast |
| **Search Quality** | Excellent | Good | Basic |
| **Memory Usage** | High | Medium | Low |
| **Semantic Search** | Yes | Limited | No |
| **Exact Matches** | Good | Excellent | Good |
| **File Size** | Large | Medium | Small |

---

## 📝 Writing Effective Knowledge Documents

### Document Structure Best Practices

1. **Clear Headings**: Use hierarchical headings (H1, H2, H3)
2. **Descriptive Titles**: Make headings searchable and specific
3. **Step-by-Step Instructions**: Break down complex processes
4. **Examples**: Include code samples and real-world examples
5. **Cross-References**: Link related topics

### Content Guidelines

#### For User Guides:
- Start with overview and getting started
- Include feature descriptions with screenshots
- Provide troubleshooting sections
- Add FAQs for common questions

#### For API Documentation:
- Include authentication details
- Provide endpoint descriptions with examples
- Document request/response formats
- Include error codes and handling

#### For Troubleshooting:
- Organize by problem categories
- Use clear problem/solution format
- Include step-by-step solutions
- Provide alternative approaches

---

## 🔍 Testing Your Knowledge Base

### Using the Chat Interface

1. **Navigate to Enhanced Chat**: Select "Enhanced Chat" in the application
2. **Test Sample Questions**:
   ```
   How do I get started with TaskFlow Pro?
   What are the different pricing plans?
   How do I create a new project?
   What should I do if I can't login?
   How do I integrate with Slack?
   ```

### Using the Knowledge API

```bash
# Search the knowledge base
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "How do I create a project?",
       "limit": 5,
       "similarity_threshold": 0.7
     }'
```

### Validation Checklist

- [ ] All documents are in `.docx` format
- [ ] Knowledge base builds without errors
- [ ] Search returns relevant results
- [ ] Chat provides accurate answers
- [ ] API endpoints respond correctly

---

## 🛠️ Troubleshooting Knowledge Base Issues

### Common Problems and Solutions

#### Knowledge Base Not Building
```bash
# Check for file permissions
ls -la Knowledge/

# Verify file formats
file Knowledge/*.docx

# Check build logs
python build_knowledge_base_robust.py --verbose
```

#### Search Returns No Results
- Verify knowledge base was built successfully
- Check that documents contain relevant content
- Try different search terms
- Rebuild the knowledge base

#### Poor Search Quality
- Use vector-based build for better semantic search
- Ensure documents have clear structure
- Add more diverse content
- Adjust similarity thresholds

#### Memory Issues During Build
- Use text-based build instead of vector-based
- Reduce document size or number
- Increase system memory
- Use lightweight build option

---

## 📊 Knowledge Base Monitoring

### Files Created During Build

#### Vector-Based Build:
- `knowledge_vector_index.faiss`: Vector index file
- `knowledge_documents.pkl`: Document metadata
- `knowledge_stats.json`: Build statistics

#### Text-Based Build:
- `knowledge_word_index.json`: Word-based index
- `knowledge_phrase_index.json`: Phrase patterns
- `knowledge_category_index.json`: Category mappings
- `knowledge_text_search.marker`: Build marker
- `knowledge_stats.json`: Build statistics

### Monitoring Commands

```bash
# Check knowledge base status
curl http://localhost:8000/stats

# List indexed documents
curl http://localhost:8000/documents

# View build statistics
cat knowledge_stats.json
```

---

## 🔄 Updating Your Knowledge Base

### Adding New Documents

1. **Add Files**: Place new `.docx` files in `Knowledge/` directory
2. **Rebuild**: Run build script or use API
   ```bash
   python build_knowledge_base_robust.py
   ```
3. **Verify**: Test new content in chat interface

### Modifying Existing Documents

1. **Edit Files**: Update content in existing documents
2. **Force Rebuild**: Use force flag to rebuild
   ```bash
   curl -X POST "http://localhost:8000/build" \
        -d '{"build_type": "vector", "force": true}'
   ```

### Best Practices for Updates

- **Backup**: Keep backups of working knowledge bases
- **Version Control**: Track document changes in git
- **Test**: Verify updates work before deployment
- **Monitor**: Check build logs for errors

---

## 🚀 Production Deployment

### Docker Deployment

The knowledge base will be automatically built during Docker container startup:

```bash
docker-compose up -d
```

### Manual Production Build

```bash
# Build optimized knowledge base
python build_knowledge_base_robust.py --optimize

# Verify build
python -c "
import os
assert os.path.exists('knowledge_vector_index.faiss')
assert os.path.exists('knowledge_documents.pkl')
print('✅ Knowledge base ready for production')
"
```

### Health Checks

```bash
# API health check
curl http://localhost:8000/health

# Knowledge base status
curl http://localhost:8000/stats
```

---

## 💡 Tips for Success

1. **Start Small**: Begin with 3-5 well-structured documents
2. **Iterate**: Test and refine based on user queries
3. **Organize**: Use clear folder structure and naming
4. **Monitor**: Track which queries work well
5. **Update**: Keep documents current and accurate
6. **Backup**: Regular backups of knowledge files
7. **Test**: Validate after every major change

---

**Ready to build your knowledge base?** Start by placing your `.docx` files in the `Knowledge/` directory and run one of the build commands above! 