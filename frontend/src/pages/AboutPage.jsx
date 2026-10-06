import React from 'react';

export default function AboutPage() {
  return (
    <div className="about-page">
      <div className="admin-card">
        <h2>Architecture & Technical Specifications</h2>
        <p className="section-description">
          Detailed technical overview of the Adaptive RAG Pipeline designed for banking policy compliance checking under Reserve Bank of India (RBI) regulations.
        </p>

        <div className="arch-grid">
          <div className="arch-item">
            <h4>1. Ingestion & Section-Aware Chunking</h4>
            <p>
              PyMuPDF (fitz) extracts text page-by-page while preserving exact page numbers. Regular expressions identify clauses, numbered sections (e.g. Chapter III, Section 5), and carry the active section into each chunk.
              Chunks are calibrated to 500-800 tokens with 10-15% overlap.
            </p>
          </div>

          <div className="arch-item">
            <h4>2. Singleton CPU Embeddings</h4>
            <p>
              <code>BAAI/bge-small-en-v1.5</code> via <code>sentence-transformers</code> running locally on CPU.
              Loaded once as a thread-safe singleton. Embeddings are L2 normalized.
              BGE query instruction prefix is applied exclusively during query embedding, never for document chunks.
            </p>
          </div>

          <div className="arch-item">
            <h4>3. Persistent ChromaDB Vector Store</h4>
            <p>
              Vector database configured in cosine distance space. Persisted locally under <code>chroma_db/</code>.
              Supports document-level isolation, immediate addition of new directives without retraining, and per-document deletion.
            </p>
          </div>

          <div className="arch-item">
            <h4>4. Calibrated Retrieval & Gatekeeping</h4>
            <p>
              Cosine similarity scores are computed for each chunk. A calibrated relevance threshold filters out ungrounded and out-of-scope queries before invocation, preventing hallucination and unnecessary LLM costs.
            </p>
          </div>

          <div className="arch-item">
            <h4>5. Grounded LLM Compliance Assessment</h4>
            <p>
              Gemini LLM operates under strict zero-shot grounded instructions with Pydantic JSON schema validation.
              Scenarios are classified into <code>COMPLIANT</code>, <code>POTENTIALLY_NON_COMPLIANT</code>, or <code>REQUIRES_FURTHER_REVIEW</code>.
              Source citations are mapped directly from chunk metadata, ensuring mathematical grounding.
            </p>
          </div>

          <div className="arch-item">
            <h4>6. Adaptive Update Flow</h4>
            <p>
              When a new RBI Master Direction or notification is released, the user uploads the PDF. The system extracts, tags, chunks, embeds, and registers the vectors in ChromaDB in real-time, making it queryable in seconds without LLM retraining or downtime.
            </p>
          </div>
        </div>

        <div className="team-callout mt-4">
          <h3>Academic Project Team</h3>
          <ul>
            <li><strong>Sandhyaa K:</strong> Backend, FastAPI, Document Processing, Gemini LLM Integration</li>
            <li><strong>Kiruthika R:</strong> RAG Pipeline, BGE Embeddings, ChromaDB, Retrieval Calibration & Evaluation</li>
            <li><strong>Pooja P B:</strong> React Frontend, UI Design, Citations/Evidence Display, End-to-End Testing</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
