"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Navbar from "../Component/nav";
import { LogoutButton } from "../Component/logout";
import styles from "./page.module.css";

export default function Add_new_product() {
    const router = useRouter();
    const API = process.env.NEXT_PUBLIC_API_URL;

    const [productData, setProductData] = useState({
        name: "",
        name_eng: "",
        cost: "",
        detail: "",
        stock_qty: "",
        brand: "",
        category_l1: "",
        category_l2: "",
        key_features: "",
        key_ingredients: "",
        suitable_for_concern: "",
        size_volume: "",
        usage_instructions: "",
        notes: ""
    });
    const [uploadedFiles, setUploadedFiles] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [isExtracting, setIsExtracting] = useState(false);
    const [extractError, setExtractError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [uploadMode, setUploadMode] = useState("file");
    const [googleUrl, setGoogleUrl] = useState("");

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setProductData((prev) => ({ ...prev, [name]: value }));
    };

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const processFiles = (files) => {
        const validFiles = Array.from(files).filter(
            (file) => file.type === "application/pdf" || file.type === "text/plain" || file.name.endsWith('.txt') || file.name.endsWith('.pdf')
        );

        if (validFiles.length !== files.length) {
            alert("Only .pdf and .txt files are allowed.");
        }

        setUploadedFiles((prev) => [...prev, ...validFiles]);
    };

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            processFiles(files);
        }
    }, []);

    const handleFileInput = (e) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            processFiles(files);
        }
    };

    const removeFile = (index) => {
        setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
    };

    const applyExtractedData = (data) => {
        if (data.products && data.products.length > 0) {
            const p = data.products[0];
            setProductData((prev) => ({
                ...prev,
                name: p.name || prev.name,
                name_eng: p.name_eng || prev.name_eng,
                detail: p.detail && p.detail !== "-" ? p.detail : prev.detail,
                cost: p.cost && p.cost !== 0 ? String(p.cost) : prev.cost,
                brand: p.brand && p.brand !== "-" ? p.brand : prev.brand,
                category_l1: p.category_l1 && p.category_l1 !== "-" ? p.category_l1 : prev.category_l1,
                category_l2: p.category_l2 && p.category_l2 !== "-" ? p.category_l2 : prev.category_l2,
                key_features: p.key_features && p.key_features !== "-" ? p.key_features : prev.key_features,
                key_ingredients: p.key_ingredients && p.key_ingredients !== "-" ? p.key_ingredients : prev.key_ingredients,
                suitable_for_concern: p.suitable_for_concern && p.suitable_for_concern !== "-" ? p.suitable_for_concern : prev.suitable_for_concern,
                size_volume: p.size_volume && p.size_volume !== "-" ? p.size_volume : prev.size_volume,
                usage_instructions: p.usage_instructions && p.usage_instructions !== "-" ? p.usage_instructions : prev.usage_instructions,
                notes: p.notes && p.notes !== "-" ? p.notes : prev.notes,
            }));
        } else {
            setExtractError("No product data found.");
        }
    };

    const handleExtract = async () => {
        if (uploadedFiles.length === 0) {
            setExtractError("Please upload at least one file first.");
            return;
        }

        setIsExtracting(true);
        setExtractError("");

        try {
            const file = uploadedFiles[0];
            const formData = new FormData();
            formData.append("file", file);

            const res = await fetch(`${API}/admin/extract_file`, {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Error ${res.status}`);
            }

            const data = await res.json();
            applyExtractedData(data);
        } catch (err) {
            setExtractError(err.message || "Failed to extract data from file.");
        } finally {
            setIsExtracting(false);
        }
    };

    const handleGoogleExtract = async () => {
        if (!googleUrl.trim()) {
            setExtractError("Please enter a Google Docs or Sheets URL.");
            return;
        }

        setIsExtracting(true);
        setExtractError("");

        try {
            const res = await fetch(`${API}/admin/google_extract_file?url=${encodeURIComponent(googleUrl)}`, {
                method: "POST",
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Error ${res.status}`);
            }

            const data = await res.json();
            applyExtractedData(data);
        } catch (err) {
            setExtractError(err.message || "Failed to extract data from Google link.");
        } finally {
            setIsExtracting(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);

        try {
            const res = await fetch(`${API}/admin/add_product`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...productData,
                    cost: parseFloat(productData.cost) || 0,
                }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Error ${res.status}`);
            }

            const data = await res.json();
            alert(`Product added successfully!\nCode: ${data.code}`);
            router.back();
        } catch (err) {
            alert(`Failed to add product: ${err.message}`);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className={styles.layout}>
            <Navbar />
            <main className={styles.main}>
                <div className={styles.header}>
                    <div>
                        <h1 className={styles.title}>Add New Product</h1>
                        <p className={styles.subtitle}>Fill in details or upload comprehensive files.</p>
                    </div>
                    <LogoutButton>Logout</LogoutButton>
                </div>

                <div className={styles.contentCard}>
                    <form className={styles.formContainer} onSubmit={handleSubmit}>

                        <div className={styles.splitLayout}>
                            <div className={styles.formSection}>
                                <h2 className={styles.sectionTitle}>Manual Entry</h2>

                                <div className={styles.inputGroup}>
                                    <label htmlFor="name" className={styles.label}>Product Name (Thai)</label>
                                    <input
                                        type="text"
                                        id="name"
                                        name="name"
                                        value={productData.name}
                                        onChange={handleInputChange}
                                        className={styles.input}
                                        placeholder="Product name"
                                        required
                                    />
                                </div>

                                <div className={styles.inputGroup}>
                                    <label htmlFor="name_eng" className={styles.label}>Product Name (Eng)</label>
                                    <input
                                        type="text"
                                        id="name_eng"
                                        name="name_eng"
                                        value={productData.name_eng}
                                        onChange={handleInputChange}
                                        className={styles.input}
                                        placeholder="Product name (eng)"
                                        required
                                    />
                                </div>

                                <div className={styles.row}>
                                    <div className={styles.inputGroup}>
                                        <label htmlFor="cost" className={styles.label}>Price (฿)</label>
                                        <input
                                            type="number"
                                            id="cost"
                                            name="cost"
                                            value={productData.cost}
                                            onChange={handleInputChange}
                                            className={styles.input}
                                            placeholder="0.00"
                                            min="0"
                                            step="0.01"
                                            required
                                        />
                                    </div>
                                    <div className={styles.inputGroup}>
                                        <label htmlFor="stock_qty" className={styles.label}>Stock Quantity</label>
                                        <input
                                            type="number"
                                            id="stock_qty"
                                            name="stock_qty"
                                            value={productData.stock_qty}
                                            onChange={handleInputChange}
                                            className={styles.input}
                                            placeholder="0"
                                            min="0"
                                            required
                                        />
                                    </div>
                                </div>

                                <div className={styles.row}>
                                    <div className={styles.inputGroup}>
                                        <label htmlFor="brand" className={styles.label}>Brand</label>
                                        <input type="text" id="brand" name="brand" value={productData.brand} onChange={handleInputChange} className={styles.input} />
                                    </div>
                                    <div className={styles.inputGroup}>
                                        <label htmlFor="size_volume" className={styles.label}>Size / Volume</label>
                                        <input type="text" id="size_volume" name="size_volume" value={productData.size_volume} onChange={handleInputChange} className={styles.input} />
                                    </div>
                                </div>

                                <div className={styles.row}>
                                    <div className={styles.inputGroup}>
                                        <label htmlFor="category_l1" className={styles.label}>Category L1</label>
                                        <input type="text" id="category_l1" name="category_l1" value={productData.category_l1} onChange={handleInputChange} className={styles.input} />
                                    </div>
                                    <div className={styles.inputGroup}>
                                        <label htmlFor="category_l2" className={styles.label}>Category L2</label>
                                        <input type="text" id="category_l2" name="category_l2" value={productData.category_l2} onChange={handleInputChange} className={styles.input} />
                                    </div>
                                </div>

                                <div className={styles.inputGroup}>
                                    <label htmlFor="detail" className={styles.label}>Detail</label>
                                    <textarea
                                        id="detail"
                                        name="detail"
                                        value={productData.detail}
                                        onChange={handleInputChange}
                                        className={styles.textarea}
                                        placeholder="Product detail..."
                                        rows="3"
                                    />
                                </div>

                                <div className={styles.inputGroup}>
                                    <label htmlFor="key_features" className={styles.label}>Key Features</label>
                                    <textarea id="key_features" name="key_features" value={productData.key_features} onChange={handleInputChange} className={styles.textarea} rows="2" />
                                </div>

                                <div className={styles.inputGroup}>
                                    <label htmlFor="key_ingredients" className={styles.label}>Key Ingredients</label>
                                    <textarea id="key_ingredients" name="key_ingredients" value={productData.key_ingredients} onChange={handleInputChange} className={styles.textarea} rows="2" />
                                </div>

                                <div className={styles.inputGroup}>
                                    <label htmlFor="suitable_for_concern" className={styles.label}>Suitable For Concern</label>
                                    <textarea id="suitable_for_concern" name="suitable_for_concern" value={productData.suitable_for_concern} onChange={handleInputChange} className={styles.textarea} rows="2" />
                                </div>

                                <div className={styles.inputGroup}>
                                    <label htmlFor="usage_instructions" className={styles.label}>Usage Instructions</label>
                                    <textarea id="usage_instructions" name="usage_instructions" value={productData.usage_instructions} onChange={handleInputChange} className={styles.textarea} rows="2" />
                                </div>

                                <div className={styles.inputGroup}>
                                    <label htmlFor="notes" className={styles.label}>Notes</label>
                                    <textarea id="notes" name="notes" value={productData.notes} onChange={handleInputChange} className={styles.textarea} rows="2" />
                                </div>
                            </div>

                            {/* Extract Section */}
                            <div className={styles.formSection}>
                                <h2 className={styles.sectionTitle}>Extract Product Data</h2>

                                <div className={styles.modeTabs}>
                                    <button
                                        type="button"
                                        className={`${styles.modeTab} ${uploadMode === "file" ? styles.modeTabActive : ""}`}
                                        onClick={() => { setUploadMode("file"); setExtractError(""); }}
                                    >
                                        Upload File
                                    </button>
                                    <button
                                        type="button"
                                        className={`${styles.modeTab} ${uploadMode === "google" ? styles.modeTabActive : ""}`}
                                        onClick={() => { setUploadMode("google"); setExtractError(""); }}
                                    >
                                        Google Link (docs or sheets)
                                    </button>
                                </div>

                                {uploadMode === "file" && (
                                    <>
                                        <p className={styles.helperText}>Upload product specifications in .pdf or .txt formats.</p>
                                        <div
                                            className={`${styles.dropZone} ${isDragging ? styles.dragging : ""}`}
                                            onDragOver={handleDragOver}
                                            onDragLeave={handleDragLeave}
                                            onDrop={handleDrop}
                                            onClick={() => document.getElementById("fileUpload").click()}
                                        >
                                            <input
                                                type="file"
                                                id="fileUpload"
                                                multiple
                                                accept=".pdf,.txt"
                                                className={styles.hiddenInput}
                                                onChange={handleFileInput}
                                            />
                                            <div className={styles.dropZoneContent}>
                                                <svg className={styles.uploadIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                                                <p className={styles.dropZoneText}>Drag & Drop files here</p>
                                                <span className={styles.dropZoneSubtext}>or click to browse</span>
                                            </div>
                                        </div>

                                        {uploadedFiles.length > 0 && (
                                            <div className={styles.fileList}>
                                                <h3 className={styles.fileListTitle}>Selected Files:</h3>
                                                <ul className={styles.files}>
                                                    {uploadedFiles.map((file, index) => (
                                                        <li key={index} className={styles.fileItem}>
                                                            <span className={styles.fileName}>{file.name}</span>
                                                            <button type="button" onClick={(e) => { e.stopPropagation(); removeFile(index); }} className={styles.removeBtn}>✕</button>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        {uploadedFiles.length > 0 && (
                                            <button
                                                type="button"
                                                className={styles.extractBtn}
                                                onClick={handleExtract}
                                                disabled={isExtracting}
                                            >
                                                {isExtracting ? (
                                                    <><span className={styles.spinner}></span> Extracting...</>
                                                ) : (
                                                    <><svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg> Extract with AI</>
                                                )}
                                            </button>
                                        )}
                                    </>
                                )}

                                {uploadMode === "google" && (
                                    <>
                                        <p className={styles.helperText}>Paste a public Google Docs or Google Sheets link. Need to set permission to public view.</p>
                                        <div className={styles.googleInputRow}>
                                            <input
                                                type="url"
                                                className={styles.input}
                                                placeholder="https://docs.google.com/document/d/..."
                                                value={googleUrl}
                                                onChange={(e) => setGoogleUrl(e.target.value)}
                                            />
                                        </div>
                                        <button
                                            type="button"
                                            className={styles.extractBtn}
                                            onClick={handleGoogleExtract}
                                            disabled={isExtracting || !googleUrl.trim()}
                                        >
                                            {isExtracting ? (
                                                <><span className={styles.spinner}></span> Extracting...</>
                                            ) : (
                                                <><svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg> Extract with AI</>
                                            )}
                                        </button>
                                    </>
                                )}

                                {extractError && (
                                    <div className={styles.extractError}>
                                        {extractError}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className={styles.actions}>
                            <button type="button" className={styles.cancelBtn} onClick={() => router.back()} disabled={isSubmitting}>Cancel</button>
                            <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
                                {isSubmitting ? (
                                    <><span className={styles.spinner}></span> Adding...</>
                                ) : (
                                    "Add Product"
                                )}
                            </button>
                        </div>

                    </form>
                </div>
            </main>
        </div>
    );
}