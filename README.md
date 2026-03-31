🛡️ Sentinel – AI Governance Layer

🚀 Overview

Sentinel is an AI governance layer designed to control, validate, and secure autonomous AI agents operating in critical environments.

It combines multi-agent risk analysis, deterministic decision logic, cryptographic integrity, and decentralized storage to ensure trustworthy AI decisions.

---

## 🖼️ System Architecture

![Image](https://github.com/user-attachments/assets/8f2e5bfa-6a28-45e4-8c4a-433126b8bd04)

---

⚠️ The Problem

Autonomous AI agents are increasingly used in finance, infrastructure, and critical systems.

However, they introduce major risks:

- Uncontrolled decision-making
- Lack of governance and oversight
- Exposure of sensitive data (PII, encryption keys)
- No verifiable audit trail

---

💡 Our Solution

Sentinel acts as a governance firewall for AI agents.

Before execution, every AI-driven action is:

1. Evaluated by multiple specialized agents
2. Scored based on risk
3. Validated through governance logic
4. Signed cryptographically
5. Stored on IPFS for auditability

---

## 🔐 Trust Layer

![Image](https://github.com/user-attachments/assets/493c34ac-e5d0-45e7-9514-8ec1be882ca0)

---

🧠 How It Works

🔹 Multi-Agent Evaluation

- Security Agent → threat modeling
- Compliance Agent → regulatory validation
- Ops Agent → operational safety

---

🔹 Deterministic Governance Engine

- Risk scoring (0–100)
- Decisions:
  - "approve"
  - "approve_with_controls"
  - "reject"

---

## 🧭 Governance & Control

![Image](https://github.com/user-attachments/assets/e771ecb3-27ab-4caf-a19c-93b7078239e0)

---

🧪 Example Scenario

Scenario:
Deploying an autonomous AI agent managing financial transaction routing across multiple subsidiaries.

Result:

- Security → Reject
- Compliance → Reject
- Ops → Approve with controls

👉 Final Decision: REJECT

---

📦 Tech Stack

- FastAPI
- OpenAI API
- Pydantic
- IPFS (Pinata)
- Ed25519 cryptography
- Python

---

⚙️ Quick Start

git clone https://github.com/sentinel-agents/sentinel-ai-governance.git

cd sentinel

python -m venv .venv
.\.venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload

---

🔑 Environment Variables

Create a ".env" file:

OPENAI_API_KEY=your_key
PINATA_JWT=your_token

---

🧪 Run the App

Open:

http://127.0.0.1:8000

Enter a scenario and run Sentinel.

---

📊 Output Includes

- Risk scores per agent
- Final decision
- Conflict detection
- Recommended controls
- SHA256 hash
- Cryptographic signature
- IPFS CID

---

🌍 Vision

Sentinel is the foundation for trustworthy autonomous AI systems.

It enables:

- Safe AI deployment
- Transparent governance
- Verifiable decision-making
- Decentralized audit trails

---

🏁 Hackathon Submission

PL Genesis – Frontiers of Collaboration

---

🤝 Future Work

- DAO-based governance
- On-chain verification
- Real-time monitoring dashboards
- Enterprise GRC integration

---

📜 License

MIT License
