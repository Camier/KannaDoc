<div align="center">
  <img src="./assets/logo.png" width="300" height="300" alt="LAYRA Logo" />
  <h1>🌌 LAYRA: Next Generation AI Agent Engine That Sees, Understands & Acts</h1>
  <p>
    <a href="https://github.com/liweiphys/layra/stargazers">
      <img src="https://img.shields.io/github/stars/liweiphys/layra?style=social" alt="GitHub Stars" />
    </a>
    <a href="https://github.com/liweiphys/layra/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/liweiphys/layra" alt="License: Apache 2.0" />
    </a>
    <a href="https://github.com/liweiphys/layra/issues">
      <img src="https://img.shields.io/github/issues-closed/liweiphys/layra" alt="Closed Issues" />
    </a>
    <a href="https://liweiphys.github.io/layra">
      <img src="https://img.shields.io/badge/Tutorial-GitHub_Pages-blue" alt="Tutorial" />
    </a>
  </p>
  <p>
    <a href="./README.md">English</a> |
    <a href="./README_zh.md">简体中文</a>
  </p>
</div>

<div align="center">
  <!-- Collapsible Group Panel -->
  <details>
    <summary>📢 Click to Expand WeChat Groups</summary>
    <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-top: 10px;">
      <div style="text-align: center;">
        <p>🚀 User Discussion Group 1</p>
        <img src="./assets/Wechat-group1.jpg" width="160" alt="User Discussion Group"/>
      </div>
      <div style="text-align: center;">
        <p>💡 Official WeChat Account</p>
        <img src="./assets/WechatOfficialAccount.jpg" width="200" alt="Official WeChat Account"/>
      </div>
    </div>
  </details>
</div>

---

> **🚀 New Jina-Embeddings-v4 API support eliminates local GPU requirements**

**LAYRA** is the world’s first “visual-native” AI automation engine. It **sees documents like a human**, preserves layout and graphical elements, and executes **arbitrarily complex workflows** with full Python control. From vision-driven Retrieval-Augmented Generation (RAG) to multi-step agent workflow orchestration, LAYRA empowers you to build next-generation intelligent systems—no limits, no compromises.

Built for **Enterprise-Grade** deployment, LAYRA features:

- **🧑‍💻 Modern Frontend:** Built with Next.js 15 (TypeScript) & TailwindCSS 4.0 for a snappy, developer-friendly UI.
- **⚡ High-Performance Backend:** FastAPI-powered with async integration for Redis, MySQL, MongoDB, Kafka & MinIO – engineered for high concurrency.
- **🔩 Decoupled Service Architecture**: Independent services deployed in dedicated containers, enabling scaling on demand and fault isolation.
- **🎯 Visual-Native Multimodal Document Understanding:** Leverages ColQwen 2.5/Jina-Embeddings-v4 to transform documents into semantic vectors stored in Milvus.
- **🚀 Powerful Workflow Engine:** Construct complex, loop-nested, and debuggable workflows with full Python execution and human-in-the-loop capabilities.

---

## 📚 Table of Contents

- [🖼️ Screenshots](#screenshots)
- [🚀 Quick Start](#quick-start)
- [📖 Tutorial Guide](#tutorial-guide)
- [❓ Why LAYRA?](#why-layra)
- [⚡️ Core Superpowers](#core-superpowers)
- [🚀 Latest Updates](#latest-updates)
- [🧠 System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [📘 API Documentation](#api-documentation)
- [📖 Technical Documentation](#technical-documentation)
- [📦 Roadmap](#roadmap)
- [🤝 Contributing](#contributing)
- [📫 Contact](#contact)
- [🌟 Star History](#star-history)
- [📄 License](#license)

---

<h2 id="screenshots">🖼️ Screenshots</h2>

- ##### LAYRA's web design consistently adheres to a minimalist philosophy, making it more accessible to new users.

Explore LAYRA's powerful interface and capabilities through these visuals:

1. **Homepage - Your Gateway to LAYRA**  
   ![Homepage Screenshot](./assets/homepage.png)

2. **Knowledge Base - Centralized Document Hub**  
   ![Knowledge Base Screenshot](./assets/knowledgebase.png)

3. **Interactive Dialogue - Layout-Preserving Answers**
   ![Layout-Preserving Answers](./assets/dialog.png)

4. **Workflow Builder - Drag-and-Drop Agent Creation**  
   ![Workflow Screenshot](./assets/workflow1.png)

5. **Workflow Builder - MCP Example**  
   ![mcp Screenshot](./assets/mcp.png)
   ![mcp Screenshot](./assets/mcp2.png)

---

<h2 id="quick-start">🚀 Quick Start</h2>

#### 📋 Prerequisites

Before starting, ensure your system meets these requirements:

1. **Docker** and **Docker Compose** installed
2. **NVIDIA Container Toolkit** configured (Ignore if not deploying ColQwen locally)

#### ⚙️ Installation Steps

##### 1. Configure Environment Variables

```bash
# Clone the repository
git clone https://github.com/liweiphys/layra.git
cd layra

# Tip: start from the template
cp .env.example .env

# Security note: `.env` contains secrets and must stay local (it is gitignored).

# Edit configuration file (modify server IP/parameters as needed)
vim .env

# Key configuration options include:
# - SERVER_IP (server IP)
# - MODEL_BASE_URL (model download source)
```

**For Jina (cloud API) Embeddings v4 users:**

```bash
vim .env
EMBEDDING_IMAGE_DPI=100 # DPI for document-to-image conversion. Recommended: 100 - 200 (12.5k - 50k tokens/img)  
EMBEDDING_MODEL=jina_embeddings_v4
JINA_API_KEY=your_jina_api_key
JINA_EMBEDDINGS_V4_URL=https://api.jina.ai/v1/embeddings 
```

##### 2. Build and Start Service

**Option A**: Local ColQwen deployment (recommended for GPUs with >16GB VRAM)

```bash
# Initial startup will download ~15GB model weights (be patient)
./scripts/compose-clean up -d --build

# Monitor logs in real-time (replace <service_name> with actual service name)
./scripts/compose-clean logs -f <service_name>
```

**Option B**: Jina-embeddings-v4 API service (for limited/no GPU resources)

```bash
# Set EMBEDDING_MODEL to jina_embeddings_v4 in .env first
# Initial startup will not download any model weights (fast!)
./scripts/compose-clean up -d --build

# Monitor logs in real-time (replace <service_name> with actual service name)
./scripts/compose-clean logs -f <service_name>
```

> **Important**: In this repo, always run Compose via `./scripts/compose-clean` (it uses a sanitized environment + `--env-file .env`). This prevents a polluted host shell from overriding `.env` values during variable interpolation. See `docs/RUNBOOK_COMPOSE_CLEAN.md`.

#### 🎉 Enjoy LAYRA!

Your deployment is complete! Start creating with Layra now. 🚀✨  
_For detailed options, see the [Deployment section](#deployment)._

> **📘 Essential Learning:** We strongly recommend spending just 60 minutes with the [tutorial](https://liweiphys.github.io/layra) before starting with LAYRA - **this small investment will help you master its full potential** and unlock advanced capabilities.

---

## <h2 id="tutorial-guide">📖 Tutorial Guide</h2>

For step-by-step instructions and visual guides, visit our tutorial on GitHub Pages:  
[Tutorial Guide](https://liweiphys.github.io/layra)

---

<h2 id="why-layra">❓ Why LAYRA?</h2>

### 🚀 Beyond RAG: The Power of Visual-First Workflows

While LAYRA's **Visual RAG Engine** revolutionizes document understanding, its true power lies in the **Agent Workflow Engine** - a visual-native platform for building complex AI agents that see, reason, and act. Unlike traditional RAG/Workflow systems limited to retrieval, LAYRA enables full-stack automation through:

### ⚙️ Advanced Workflow Capabilities

- **🔄 Cyclic & Nested Structures**  
  Build recursive workflows with loop nesting, conditional branching, and custom Python logic - no structural limitations.

- **🐞 Node-Level Debugging**  
  Inspect variables, pause/resume execution, and modify state mid-workflow with visual breakpoint debugging.

- **👤 Human-in-the-Loop Integration**  
  Inject user approvals at critical nodes for collaborative AI-human decision making.

- **🧠 Chat Memory & MCP Integration**  
  Maintain context across nodes with chat memory and access live information via Model Context Protocol (MCP).

- **🐍 Full Python Execution**  
  Run arbitrary Python code with `pip` installs, HTTP requests, and custom libraries in sandboxed environments.

- **🎭 Multimodal I/O Orchestration**  
  Process and generate hybrid text/image outputs across workflow stages.

### 🔍 Visual RAG: The Seeing Engine

Traditional RAG systems fail because they:

- ❌ **Lose layout fidelity** (columns, tables, hierarchy collapse)
- ❌ **Struggle with non-text visuals** (charts, diagrams, figures)
- ❌ **Break semantic continuity** due to poor OCR segmentation

**LAYRA changes this with pure visual embeddings:**

> 🔍 It sees each page as a whole - just like a human reader - preserving:
>
> - ✅ Layout structure (headers, lists, sections)
> - ✅ Tabular integrity (rows, columns, merged cells)
> - ✅ Embedded visuals (plots, graphs, stamps, handwriting)
> - ✅ Multi-modal consistency between layout and content

**Together, these engines form the first complete visual-native agent platform - where AI doesn't just retrieve information, but executes complex vision-driven workflows end-to-end.**

---

<h2 id="core-superpowers">⚡️ Core Superpowers</h2>

### 🔥 **The Agent Workflow Engine: Infinite Execution Intelligence**

> **Code Without Limits, Build Without Boundaries**
> Our Agent Workflow Engine thinks in LLM, sees in visuals, and builds your logic in Python — no limits, just intelligence.

- **🔄 Unlimited Workflow Creation**  
  Design complex custom workflows **without structural constraints**. Handle unique business logic, branching, loops, and conditions through an intuitive interface.

- **⚡ Real-Time Streaming Execution (SSE)**  
  Observe execution results streamed **live** – eliminate waiting times entirely.

- **👥 Human-in-the-Loop Integration**  
  **Integrate user input** at critical decision points to review, adjust, or direct model reasoning. Enables collaborative AI workflows with dynamic human oversight.

- **👁️ Visual-First Multimodal RAG**  
  Features LAYRA’s proprietary **pure visual embedding system**, delivering lossless document understanding across **100+ formats** (PDF, DOCX, XLSX, PPTX, etc.). The AI actively "sees" your content.

- **🧠 Chat Memory & MCP Integration**

  - **MCP Integration** Access and interact with live, evolving information beyond native context windows – enhancing adaptability for long-term tasks.
  - **ChatFlow Memory** Maintain contextual continuity through chat memory, enabling personalized interactions and intelligent workflow evolution.

- **🐍 Full-Stack Python Control**

  - Drive logic with **arbitrary Python expressions** – conditions, loops, and more
  - Execute **unrestricted Python code** in nodes (HTTP, AI calls, math, etc.)
  - **Sandboxed environments** with secure pip installs and persistent runtime snapshots

- **🎨 Flexible Multimodal I/O**  
  Process and generate text, images, or hybrid outputs – ideal for cross-modal applications.

- **🔧 Advanced Development Suite**

  - **Breakpoint Debugging**: Inspect workflow states mid-execution
  - **Reusable Components**: Import/export workflows and save custom nodes
  - **Nested Logic**: Construct deeply dynamic task chains with loops and conditionals

- **🧩 Intelligent Data Utilities**
  - Extract variables from LLM outputs
  - Parse JSON dynamically
  - Template rendering engine  
    Essential tools for advanced AI reasoning and automation.

### 👁️ Visual RAG Engine: Beyond Text, Beyond OCR

> **Forget tokenization. Forget layout loss.**  
> With pure visual embeddings, LAYRA understands documents like a human — page by page, structure and all.

**LAYRA** uses next-generation Retrieval-Augmented Generation (RAG) technology powered by **pure visual embeddings**. It treats documents not as sequences of tokens but as visually structured artifacts — preserving layout, semantics, and graphical elements like tables, figures, and charts.

---

<h2 id="latest-updates">🚀 Latest Updates</h2>

**(2025.8.4) ✨ Expanded Embedding Model Support**:

- **More Embedding Model Support**:
  - `colqwen` (Local GPU - high performance)
  - `jina-embeddings-v4` (Cloud API - zero GPU requirements)
- **New Chinese language support**

**(2025.6.2) Workflow Engine Now Available**:

- **Breakpoint Debugging**: Debug workflows interactively with pause/resume functionality.
- **Unrestricted Python Customization**: Execute arbitrary Python code, including external `pip` dependency installation, HTTP requests via `requests`, and advanced logic.
- **Nested Loops & Python-Powered Conditions**: Build complex workflows with loop nesting and Python-based conditional logic.
- **LLM Integration**:
  - Automatic JSON output parsing for structured responses.
  - Persistent conversation memory across nodes.
  - File uploads and knowledge-base retrieve with **multi-modal RAG** supporting 100+ formats (PDF, DOCX, XLSX, PPTX, etc.).

**(2025.4.6) First Trial Version Now Available**:  
 The first testable version of LAYRA has been released! Users can now upload PDF documents, ask questions, and receive layout-aware answers. We’re excited to see how this feature can help with real-world document understanding.

- **Current Features**:
  - PDF batch upload and parsing functionality
  - Visual-first retrieval-augmented generation (RAG) for querying document content
  - Backend fully optimized for scalable data flow with **FastAPI**, **Milvus**, **Redis**, **MongoDB**, and **MinIO**

Stay tuned for future updates and feature releases!

---

<h2 id="system-architecture">🧠 System Architecture</h2>

LAYRA’s pipeline is designed for **async-first**, **visual-native**, and **scalable document retrieval and generation**.

### 🔍 Query Flow

The query goes through embedding → vector retrieval → anser generation:

![Query Architecture](./assets/query.png)

### 📤 Upload & Indexing Flow

PDFs are parsed into images and embedded visually via ColQwen2.5/Jina-Embeddings-v4, with metadata and files stored in appropriate databases:

![Upload Architecture](./assets/upload.png)

### 📤 Execute Workflow (Chatflow)

The workflow execution follows an **event-driven**, **stateful debugging** pattern with granular control:

#### 🔄 Execution Flow

1. **Trigger & Debug Control**

   - Web UI submits workflow with **configurable breakpoints** for real-time inspection
   - Backend validates workflow DAG before executing codes

2. **Asynchronous Orchestration**

   - Kafka checks **predefined breakpoints** and triggers pause notifications
   - Scanner performs **AST-based code analysis** with vulnerability detection

3. **Secure Execution**

   - Sandbox spins up ephemeral containers with file system isolation
   - Runtime state snapshots persisted to _Redis/MongoDB_ for recovery

4. **Observability**
   - Execution metrics streamed via Server-Sent Events (SSE)
   - Users inject test inputs/resume execution through debug consoles

![Upload Architecture](./assets/workflow.png)

---

<h2 id="tech-stack">🧰 Tech Stack</h2>

**Frontend**:

- `Next.js`, `TypeScript`, `TailwindCSS`, `Zustand`, `xyflow`

**Backend & Infrastructure**:

- `FastAPI`, `Kafka`, `Redis`, `MySQL`, `MongoDB`, `MinIO`, `Milvus`, `Docker`

**Models & RAG**:

- Embedding: `colqwen2.5-v0.2` `jina-embeddings-v4`
- LLM Serving: `Qwen2.5-VL series (or any OpenAI-compatible model)`
  [LOCAL DEPLOYMENT NOTE](https://liweiphys.github.io/layra/docs/RAG-Chat)

---

<h2 id="deployment">⚙️ Deployment</h2>

### 🎯 Deployment Modes

LAYRA supports multiple deployment configurations for different use cases:

| Mode | Compose File | Description | Use Case |
|------|--------------|-------------|----------|
| **Standard (GPU)** | `docker-compose.yml` | Full deployment with local ColQwen2.5 embeddings | Production, research, development with NVIDIA GPU |
| **Jina API (No GPU)** | `docker-compose.yml` (set `EMBEDDING_MODEL=jina_embeddings_v4`) | Cloud embeddings via Jina API | Limited/no GPU resources, quick testing |
| **Thesis/Solo** | `deploy/docker-compose.thesis.yml` | Simplified single-user deployment with Neo4j | Thesis demonstrations, solo research, simplified auth |
| **Development** | `docker-compose.override.yml` | Development overrides (extends base) | Local development with custom settings |

#### Key Differences:

- **Standard**: Full feature set, requires 16GB+ GPU VRAM for ColQwen2.5
- **Jina API**: No local GPU needed, uses cloud API (requires Jina API key) - same compose file, different env config
- **Thesis**: Simplified for single-user, includes Neo4j graph database (infrastructure-ready, application integration verified)
- **Development**: Local development overrides (hot reload, debug settings)

> **Note**: All modes use the same `.env` configuration. Copy `.env.example` to `.env` and adjust values for your deployment.

#### 📋 Prerequisites

Before starting, ensure your system meets these requirements:

1. **Docker** and **Docker Compose** installed
2. **NVIDIA Container Toolkit** configured (Ignore if not deploying ColQwen locally)

#### ⚙️ Installation Steps

##### 1. Configure Environment Variables

```bash
# Clone the repository
git clone https://github.com/liweiphys/layra.git
cd layra

# Edit configuration file (modify server IP/parameters as needed)
vim .env

# Key configuration options include:
# - SERVER_IP (public server IP)
# - MODEL_BASE_URL (model download source)
```

**For Jina (cloud API) Embeddings v4 users:**

```bash
vim .env
EMBEDDING_IMAGE_DPI=100 # DPI for document-to-image conversion. Recommended: 100 - 200 (12.5k - 50k tokens/img)  
EMBEDDING_MODEL=jina_embeddings_v4
JINA_API_KEY=your_jina_api_key
JINA_EMBEDDINGS_V4_URL=https://api.jina.ai/v1/embeddings 
```

##### 2. Build and Start Service

**Option A**: Standard GPU Deployment (recommended for GPUs with >16GB VRAM)

```bash
# Initial startup will download ~15GB model weights (be patient)
./scripts/compose-clean up -d --build  # Uses docker-compose.yml (default)

# Monitor logs in real-time (replace <service_name> with actual service name)
./scripts/compose-clean logs -f <service_name>
```

**Option B**: Jina API Deployment (no local GPU required)

```bash
# First, set EMBEDDING_MODEL=jina_embeddings_v4 and JINA_API_KEY in .env
# Uses cloud embeddings via Jina API (no local model download)
./scripts/compose-clean up -d --build

# Monitor logs in real-time
./scripts/compose-clean logs -f <service_name>
```

**Option C**: Thesis/Solo Deployment (simplified single-user)

```bash
# For thesis demonstrations or single-user research with Neo4j (infrastructure-ready, application integration verified)
./scripts/deploy-thesis.sh  # Automated deployment script

# Or manually:
# cp .env.example .env (then edit for your setup)
# docker compose -f deploy/docker-compose.thesis.yml --env-file .env up -d --build
```

**📚 Thesis Deployment Guide**: See [`docs/THESIS_QUICKSTART.md`](docs/THESIS_QUICKSTART.md) for detailed instructions, verification steps, and Milvus connectivity notes.

**✅ Current Verification (2026-01-22)**:
- 26 PDFs ingested (ethnopharmacology focus: Sceletium tortuosum, PDE4 inhibitors, monoamine oxidase, etc.)
- 180,208 vector embeddings stored in Milvus (ColQwen image embeddings)
- GPU embeddings operational via ColQwen2.5 (model-server GPU)
- Neo4j accessible at http://localhost:7474 (password: from NEO4J_PASSWORD)
- Frontend: http://localhost:8090 (user: `thesis`, password: `thesis_deploy_b20f1508a2a983f6`)
- Knowledge Base ID: `thesis_34f1ab7f-5fbe-4a7a-bf73-6561f8ce1dd7`
- Workflow deployed: `thesis_74a550b6-1746-4e4f-b9c0-881ac8717341` (Thesis Blueprint Minutieux V1)
- Workflow execution started: Task ID `a12ae5c9-f051-4c2e-b26a-39d5ab6cbe7d`
- API accessible with JWT token (see quickstart for examples)
- Milvus internal connectivity confirmed (port 19530 not exposed to host)

> **Important**: In this repo, always run Compose via `./scripts/compose-clean` (it uses a sanitized environment + `--env-file .env`). This prevents a polluted host shell from overriding `.env` values during variable interpolation. See `docs/RUNBOOK_COMPOSE_CLEAN.md`.

#### 🔧 Troubleshooting Tips

If services fail to start:

```bash
# Check container logs:
./scripts/compose-clean logs <service_name>
```

Common fixes:

```bash
nvidia-smi  # Verify GPU detection
./scripts/compose-clean down && ./scripts/compose-clean up -d --build  # preserve data to rebuild
./scripts/compose-clean down -v && ./scripts/compose-clean up -d --build  # ⚠️ Caution: delete all data to full rebuild
```

#### 🛠️ Service Management Commands

Choose the operation you need:

| **Scenario**                               | **Command**                                     | **Effect**                                 |
| ------------------------------------------ | ----------------------------------------------- | ------------------------------------------ |
| **Stop services**<br>(preserve data)       | `./scripts/compose-clean stop`                          | Stops containers but keeps them intact     |
| **Restart after stop**                     | `./scripts/compose-clean start`                         | Restarts stopped containers                |
| **Rebuild after code changes**             | `./scripts/compose-clean up -d --build`                 | Rebuilds images and recreates containers   |
| **Recreate containers**<br>(preserve data) | `./scripts/compose-clean down`<br>`./scripts/compose-clean up -d` | Destroys then recreates containers         |
| **Full cleanup**<br>(delete all data)      | `./scripts/compose-clean down -v`                       | ⚠️ Destroys containers and deletes volumes |

#### ⚠️ Important Notes

1. **Initial model download** may take significant time (~15GB). Monitor progress:

	   ```bash
	   ./scripts/compose-clean logs -f model-weights-init
	   ```

2. **After modifying `.env` or code**, always rebuild:

	   ```bash
	   ./scripts/compose-clean up -d --build
	   ```

3. **Verify NVIDIA toolkit** installation:

   ```bash
   nvidia-container-toolkit --version
   ```

4. **For network issues**:
   - Manually download model weights
   - Copy to Docker volume: (typically at) `/var/lib/docker/volumes/layra_model_weights/_data/`
   - Create empty `complete.layra` file in both:
     - **`colqwen2.5-base`** folder
     - **`colqwen2.5-v0.2`** folder
   - 🚨 **Critical**: Verify downloaded weights integrity!

5. **Milvus Vector Database Access**:
   - Milvus port 19530 is **not exposed to host** for security
   - Services access internally via `milvus-standalone:19530`
   - Diagnostic scripts must run inside containers:
     ```bash
     docker exec layra-backend python3 -c "from pymilvus import MilvusClient; client = MilvusClient('http://milvus-standalone:19530'); print(client.list_collections())"
     ```

#### 🔑 Key Details

- `./scripts/compose-clean down -v` **permanently deletes** databases and model weights
- **After code/config changes**, always use `--build` flag
- **GPU requirements**:
  - Latest NVIDIA drivers
  - Working `nvidia-container-toolkit`
- **Monitoring tools**:

	  ```bash
	  # Container status
	  ./scripts/compose-clean ps -a

	  # Resource usage
	  docker stats
	  ```

> 🧪 **Technical Note**: All components run exclusively via Docker containers.

#### 🎉 Enjoy Your Deployment!

Now that everything is running smoothly, happy building with Layra! 🚀✨

#### ▶️ Future Deployment Options

In the future, we will support multiple deployment methods including Kubernetes (K8s), and other environments. More details will be provided when these deployment options are available.

---

<h2 id="api-documentation">📘 API Documentation</h2>

LAYRA provides comprehensive interactive API documentation through FastAPI's built-in Swagger UI and ReDoc.

### Access Points

| Documentation | URL | Description |
|--------------|-----|-------------|
| **Swagger UI** | `http://localhost:8090/api/docs` | Interactive API explorer with try-it-out functionality |
| **ReDoc** | `http://localhost:8090/api/redoc` | Alternative documentation with detailed specs |

### Key Endpoints

| Category | Base Path | Description |
|----------|-----------|-------------|
| **Authentication** | `/api/v1/auth/*` | Login, logout, token verification |
| **Workflows** | `/api/v1/workflow/*` | Create, execute, list workflows |
| **Chat** | `/api/v1/chat/*` | Real-time SSE chat with RAG |
| **Knowledge Base** | `/api/v1/knowledge-base/*` | Create, list, manage knowledge bases |
| **Health** | `/api/v1/health/*` | System health checks and metrics |
| **Configuration** | `/api/v1/config/*` | Model and system configuration |

### Detailed References

For in-depth technical details, please refer to:

- [**API Reference**](docs/API.md) - Full list of endpoints, request/response formats, and examples.
- [**Database Schema**](docs/DATABASE.md) - Comprehensive overview of MySQL, MongoDB, Milvus, and Redis structures.
- [**Configuration Guide**](docs/CONFIGURATION.md) - Reference for all environment variables and system settings.

<h2 id="technical-documentation">📖 Technical Documentation</h2>

Additional technical guides and analysis:

- [**LAYRA Deep Analysis**](docs/LAYRA_DEEP_ANALYSIS.md) - Architectural deep-dive and design principles.
- [**Milvus Ingestion Plan**](docs/MILVUS_INGESTION_PLAN.md) - Optimization strategy for high-performance vector storage.
- [**GPU Optimization**](docs/GPU_OPTIMIZATION_INSIGHTS.md) - Insights on maximizing ColQwen2.5 performance.

---

<h2 id="roadmap">📦 Roadmap</h2>

**Short-term:**

- ~~Add API Support (completed)~~ ✓ OpenAPI/Swagger documentation available
- Enhanced security (CORS configurable, .env tracking fixed)

**Long-term:**

- Our evolving roadmap adapts to user needs and AI breakthroughs. New technologies and features will be deployed continuously.

---

<h2 id="contributing">🤝 Contributing</h2>

Contributions are welcome! Feel free to open an issue or pull request if you’d like to contribute.  
We are in the process of creating a CONTRIBUTING.md file, which will provide guidelines for code contributions, issue reporting, and best practices. Stay tuned!

---

<h2 id="contact">📫 Contact</h2>

**liweiphys**  
📧 liweixmu@foxmail.com  
🐙 [github.com/liweiphys/layra](https://github.com/liweiphys/layra)  
📺 [bilibili: Biggestbiaoge](https://www.bilibili.com/video/BV1sd7QzmEUg/?share_source=copy_web)  
🔍 Wechat Official Account：LAYRA 项目  
💡 Wechat group: see below the title at the top  
💼 Exploring Impactful Opportunities - Feel Free To Contact Me!

---

<h2 id="star-history">🌟 Star History</h2>

[![Star History Chart](https://api.star-history.com/svg?repos=liweiphys/layra&type=Date)](https://www.star-history.com/#liweiphys/layra&Date)

---

<h2 id="license">📄 License</h2>

This project is licensed under the **Apache License 2.0**. See the [LICENSE](./LICENSE) file for more details.

---

> _Endlessly Customizable Agent Workflow Engine - Code Without Limits, Build Without Boundaries._
