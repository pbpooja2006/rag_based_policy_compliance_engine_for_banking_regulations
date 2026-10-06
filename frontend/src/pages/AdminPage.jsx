import React, { useState, useEffect } from 'react';
import { getDocuments, uploadDocument, deleteDocument, reindexDocuments } from '../services/api';

const DEFAULT_CATEGORIES = [
  'KYC & Customer Due Diligence',
  'Fraud Risk Management',
  'Digital Lending & FinTech',
  'Customer Protection & Grievance',
  'Cyber Security & IT Governance',
  'Credit & Lending Operations',
  'General Regulatory Directive',
];

export default function AdminPage({ onDocsChanged }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Upload Form State
  const [file, setFile] = useState(null);
  const [category, setCategory] = useState(DEFAULT_CATEGORIES[0]);
  const [customCategory, setCustomCategory] = useState('');
  const [publicationDate, setPublicationDate] = useState('');
  const [effectiveDate, setEffectiveDate] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState(null); // 'extracting' | 'chunking' | 'embedding' | 'storing' | 'completed' | null
  const [reindexing, setReindexing] = useState(false);

  const fetchDocs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDocuments();
      setDocuments(data);
      if (onDocsChanged) onDocsChanged(data);
    } catch (err) {
      setError(err.message || 'Failed to load documents.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      if (!selected.name.toLowerCase().endsWith('.pdf')) {
        setError('Only official PDF documents are supported.');
        setFile(null);
        return;
      }
      setFile(selected);
      setError(null);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please choose a PDF document to upload.');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccessMsg(null);
    setUploadStep('extracting');

    // Simulate step progress while request runs
    const timer1 = setTimeout(() => setUploadStep('chunking'), 800);
    const timer2 = setTimeout(() => setUploadStep('embedding'), 1800);
    const timer3 = setTimeout(() => setUploadStep('storing'), 2800);

    try {
      const finalCategory = category === 'Custom' ? customCategory : category;
      const res = await uploadDocument(
        file,
        finalCategory,
        publicationDate || null,
        effectiveDate || null
      );

      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);

      setUploadStep('completed');
      setSuccessMsg(
        `Successfully indexed "${res.name}" with ${res.chunks_count} searchable chunks! The RAG pipeline has updated adaptively.`
      );
      setFile(null);
      setCustomCategory('');
      setPublicationDate('');
      setEffectiveDate('');

      // Refresh table
      await fetchDocs();
    } catch (err) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setError(err.message || 'Failed to upload and index document.');
      setUploadStep(null);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId, docName) => {
    if (
      !window.confirm(
        `Are you sure you want to remove "${docName}" from the compliance database? Its chunks will be deleted immediately.`
      )
    ) {
      return;
    }

    setError(null);
    try {
      await deleteDocument(docId);
      setSuccessMsg(`Document "${docName}" removed successfully.`);
      await fetchDocs();
    } catch (err) {
      setError(err.message || 'Failed to delete document.');
    }
  };

  const handleReindex = async () => {
    if (
      !window.confirm(
        'Re-index all documents in the raw data folder? This clears and regenerates all chunk embeddings in ChromaDB.'
      )
    ) {
      return;
    }

    setReindexing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await reindexDocuments();
      setSuccessMsg(res.message || 'Knowledge base successfully reindexed.');
      await fetchDocs();
    } catch (err) {
      setError(err.message || 'Failed to reindex knowledge base.');
    } finally {
      setReindexing(false);
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-header-row">
        <div>
          <h2>Adaptive Regulatory Knowledge Base</h2>
          <p className="section-description">
            Upload newly released RBI Master Directions, circulars, or notifications. The document is instantly parsed, section-tagged, chunked, and embedded into the vector store without requiring model retraining.
          </p>
        </div>
        <div className="admin-actions-bar">
          <button
            type="button"
            className="secondary-btn"
            onClick={fetchDocs}
            disabled={loading}
          >
            Refresh List
          </button>
          <button
            type="button"
            className="secondary-btn warning-action"
            onClick={handleReindex}
            disabled={reindexing || loading}
          >
            {reindexing ? 'Reindexing...' : 'Reindex All Docs'}
          </button>
        </div>
      </div>

      {/* Status Banners */}
      {error && (
        <div className="error-alert">
          <span>{error}</span>
          <button type="button" className="close-alert-btn" onClick={() => setError(null)}>&times;</button>
        </div>
      )}
      {successMsg && (
        <div className="success-alert">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>{successMsg}</span>
          <button type="button" className="close-alert-btn" onClick={() => setSuccessMsg(null)}>&times;</button>
        </div>
      )}

      {/* Upload Box */}
      <div className="admin-card upload-card">
        <h3>Upload New RBI Regulation</h3>
        <form onSubmit={handleUpload} className="upload-form">
          <div className="form-grid">
            <div className="form-group file-group">
              <label>Select Official RBI PDF Document <span className="req">*</span></label>
              <div className="file-input-wrapper">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  disabled={uploading}
                  id="pdf-upload-input"
                />
                <label htmlFor="pdf-upload-input" className="file-drop-zone">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  <span>{file ? file.name : 'Click or drag RBI PDF here'}</span>
                  <span className="file-subtext">PyMuPDF will extract text, headings & clauses</span>
                </label>
              </div>
            </div>

            <div className="form-group">
              <label>Regulatory Category <span className="req">*</span></label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                disabled={uploading}
                className="form-select"
              >
                {DEFAULT_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
                <option value="Custom">Other / Custom Category...</option>
              </select>

              {category === 'Custom' && (
                <input
                  type="text"
                  placeholder="Enter custom category name"
                  value={customCategory}
                  onChange={(e) => setCustomCategory(e.target.value)}
                  className="form-input mt-2"
                  required
                />
              )}

              <div className="date-fields-grid mt-3">
                <div>
                  <label className="sub-label">Publication Date (if printed)</label>
                  <input
                    type="date"
                    value={publicationDate}
                    onChange={(e) => setPublicationDate(e.target.value)}
                    className="form-input"
                    disabled={uploading}
                  />
                </div>
                <div>
                  <label className="sub-label">Effective Date (if printed)</label>
                  <input
                    type="date"
                    value={effectiveDate}
                    onChange={(e) => setEffectiveDate(e.target.value)}
                    className="form-input"
                    disabled={uploading}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Stepper progress indicator during upload */}
          {uploading && (
            <div className="upload-stepper">
              <div className={`step-item ${uploadStep === 'extracting' ? 'current' : 'done'}`}>
                <span className="step-num">1</span>
                <span className="step-text">PyMuPDF Text Extract</span>
              </div>
              <div className="step-arrow">&rarr;</div>
              <div className={`step-item ${uploadStep === 'chunking' ? 'current' : uploadStep === 'extracting' ? '' : 'done'}`}>
                <span className="step-num">2</span>
                <span className="step-text">Section-Aware Chunking</span>
              </div>
              <div className="step-arrow">&rarr;</div>
              <div className={`step-item ${uploadStep === 'embedding' ? 'current' : ['extracting', 'chunking'].includes(uploadStep) ? '' : 'done'}`}>
                <span className="step-num">3</span>
                <span className="step-text">BGE CPU Embedding</span>
              </div>
              <div className="step-arrow">&rarr;</div>
              <div className={`step-item ${uploadStep === 'storing' ? 'current' : uploadStep === 'completed' ? 'done' : ''}`}>
                <span className="step-num">4</span>
                <span className="step-text">ChromaDB Persistent Store</span>
              </div>
            </div>
          )}

          <div className="form-submit-row">
            <button
              type="submit"
              className="primary-btn"
              disabled={uploading || !file}
            >
              {uploading ? 'Processing & Indexing Document...' : 'Upload & Adapt Knowledge Base'}
            </button>
          </div>
        </form>
      </div>

      {/* Indexed Documents Table */}
      <div className="admin-card">
        <div className="table-header-row">
          <h3>Currently Indexed Regulations ({documents.length})</h3>
          <span className="table-caption">
            All stored in ChromaDB persistent collection: <code>rbi_banking_regulations</code>
          </span>
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <span>Loading active indexed documents...</span>
          </div>
        ) : documents.length === 0 ? (
          <div className="empty-table-state">
            <p>No regulations currently indexed in ChromaDB.</p>
            <p className="subtext">Upload official RBI PDFs above to make them instantly searchable.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="documents-table">
              <thead>
                <tr>
                  <th>Document Title / File</th>
                  <th>Category</th>
                  <th>Chunks</th>
                  <th>Publication / Effective</th>
                  <th>Uploaded At</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.document_id}>
                    <td className="doc-name-cell">
                      <strong>{doc.name}</strong>
                      <span className="doc-id-sub">{doc.document_id}</span>
                    </td>
                    <td>
                      <span className="category-chip">{doc.category}</span>
                    </td>
                    <td>
                      <span className="chunks-count-chip">{doc.chunk_count} chunks</span>
                    </td>
                    <td className="date-cell">
                      <span>Pub: {doc.publication_date || 'N/A'}</span>
                      <span>Eff: {doc.effective_date || 'N/A'}</span>
                    </td>
                    <td className="date-cell">
                      {new Date(doc.upload_date).toLocaleDateString()}
                    </td>
                    <td>
                      <span className="status-chip indexed">Indexed</span>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="delete-btn"
                        onClick={() => handleDelete(doc.document_id, doc.name)}
                        title="Delete this document and all its chunks"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
