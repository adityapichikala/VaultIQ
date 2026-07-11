# VaultIQ — The Smart Enterprise Search Assistant

> Segment 5 · Problem E3 · LLM Systems & Applied GenAI  
> **Built by:** Pichikala Aditya | **Target role:** LLM Engineer / GenAI Engineer

---

## 🎯 Project Objective

Imagine working at a large company where important information is scattered everywhere: inside **PDFs**, **Slack conversations**, **Markdown wikis**, and **CSV spreadsheets**. When an employee has a question, finding the right answer is a nightmare.

**VaultIQ solves this problem.** It is an intelligent search assistant that reads through all of a company's messy, scattered data and uses Artificial Intelligence to answer questions accurately. Most importantly, it uses **Role-Based Access Control (ACL)**—meaning an intern cannot ask the AI to summarize confidential HR salary spreadsheets that only executives should see.

---

## 🏗️ Our Approach & Architecture (How It Works)

To build this, we used a cutting-edge AI architecture called **Retrieval-Augmented Generation (RAG)**. Here is a simple breakdown of how the system works behind the scenes when you ask it a question:

1. **Ingestion (Reading the Data):** The system automatically reads all company files (**PDFs, Slack, CSVs, Markdown**) and chops them up into small, readable chunks of text.
2. **Storage (Brain of the System):** We convert these text chunks into mathematical numbers (called **Vector Embeddings**) using the **all-MiniLM-L6-v2** AI model. We store these numbers securely in a vector database called **Qdrant**, alongside a traditional keyword database called **BM25**.
3. **Hybrid Search (Finding the Answer):** When you ask a question, the system searches both databases simultaneously to find the exact paragraphs that contain your answer. We combine these results using a technique called **Reciprocal Rank Fusion (RRF)**.
4. **Security Filter (ACL):** Before the AI sees the information, the system checks your employee role (e.g., Engineering, HR). It permanently **blocks** any secret files you aren't allowed to see.
5. **AI Generation (Speaking to You):** Finally, we send the approved, relevant paragraphs to a powerful Large Language Model (**Groq Llama-3-8B**). The AI reads the context and writes a perfect, conversational answer for you, complete with **inline citations** proving exactly where it got the information.

![Architecture Diagram](docs/architecture.md)
*(For a deeper technical dive, please see the architecture diagram and ADR documents in the `/docs` folder).*

---

## 🌟 What Makes This Project Stand Out (Key Features)

- **Role-Based Access Control (ACL):** The AI strictly enforces document security at the database level.
- **Hybrid Retrieval Pipeline:** By combining semantic meaning (**Qdrant vectors**) with exact keyword matching (**BM25 sparse index**), the search engine rarely misses an answer.
- **Multi-Modal Data Handling:** It doesn't just read plain text; it parses messy enterprise data formats like Slack JSON threads and CSV tables.
- **Lightning Fast AI:** Powered by the **Groq AI Engine**, answers are generated almost instantly.

---

## 💻 What It Looks Like After Completion

When the project is fully running, you will be presented with a clean, interactive **Streamlit Chat Interface**. 
- On the left sidebar, you can use a dropdown menu to select your "Role" (e.g., HR, Engineering, Leadership).
- In the center, you can chat with the AI just like ChatGPT.
- When the AI answers, it will provide clickable **Source Citations** so you can see the exact document it used to formulate its answer.

---

## 📅 Project Timeline & Weekly Breakdown

This project was carefully planned and executed over a **4-week timeline**:

- **Week 1 (Foundation):** Defined the problem statement, generated the massive synthetic enterprise dataset, and built the initial Python parsers to read the files.
- **Week 2 (Core RAG & UI):** Built the document chunking logic, implemented the **Qdrant** and **BM25** databases, wrote the hybrid search fusion, connected the **Groq LLM**, and built the entire **Streamlit** user interface.
- **Week 3 (Hardening & Testing):** Focused on enterprise reliability. Wrote automated **pytest** suites, set up **GitHub Actions** for Continuous Integration (CI), added robust error handling, and drafted technical architecture memos (ADRs).
- **Week 4 (Deployment - Upcoming):** Finalizing the live deployment of the app to a public URL and polishing the final "Thinking Artifacts" for recruiters.

---

## 🚀 Step-by-Step Installation Guide

Want to run VaultIQ on your own computer? Follow these simple steps. You don't need to be a developer to get this working!

### Step 1: Prerequisites
You will need two things installed on your computer:
1. **Python** (Version 3.10 or newer)
2. A free **Groq API Key**. You can get one in 30 seconds by logging in at [console.groq.com](https://console.groq.com) and clicking "Create API Key".

### Step 2: Download the Code
Open your computer's terminal (or command prompt) and run this command to download the project:
```bash
git clone https://github.com/adityapichikala/VaultIQ.git
cd VaultIQ
```

### Step 3: Setup the Environment
We will create a safe, isolated environment for the code to run in, and then install the required packages:
```bash
# Create the virtual environment
python -m venv venv

# Activate it (If you are on Windows):
venv\Scripts\activate
# Activate it (If you are on Mac/Linux):
source venv/bin/activate

# Install the required software
pip install -r requirements.txt
```

### Step 4: Add Your AI Key
In the `VaultIQ` folder, create a new text file named exactly `.env`. Inside that file, paste your Groq API key like this:
```text
GROQ_API_KEY=gsk_your_secret_key_here
```

### Step 5: Build the Search Brain
Run this command to have the system read the dummy company data, build the vector database, and prepare the search engine. *(Note: This might take 1-2 minutes the first time you run it!)*
```bash
python -m src.retrieval.build_index
```

### Step 6: Launch the App!
Run this final command to start the user interface:
```bash
streamlit run src/app/streamlit_app.py
```
Your browser will automatically open to `http://localhost:8501`, and you can start chatting with VaultIQ!

---

## License
MIT License
