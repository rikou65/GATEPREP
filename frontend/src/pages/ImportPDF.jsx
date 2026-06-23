import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { Loader2, UploadCloud, Link as LinkIcon, FileText } from "lucide-react";
import Layout from "@/components/Layout";
import { useNavigate } from "react-router-dom";

export default function ImportPDF() {
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");
  const [uploadMode, setUploadMode] = useState("file"); // "file" or "url"
  const [engine, setEngine] = useState("llama"); // "ocr" or "local" or "llama"
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/subjects").then((res) => setSubjects(res.data?.data || []));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!subjectId) {
      toast.error("Please select a subject.");
      return;
    }
    if (uploadMode === "file" && !file) {
      toast.error("Please select a PDF file.");
      return;
    }
    if (uploadMode === "url" && !url) {
      toast.error("Please enter a PDF URL.");
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("subject_id", subjectId);
      formData.append("engine", engine);
      if (uploadMode === "file") {
        formData.append("file", file);
      } else {
        formData.append("url", url);
      }

      await api.post("/admin/import/pdf", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      
      toast.success(`PDF sent to ${engine === 'ocr' ? 'OCR pipeline' : 'Local Parser'}. Check Staging Queue!`);
      navigate("/admin/staging");
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || "Failed to start import.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="Import GO-PDF">
      <div className="max-w-2xl mx-auto space-y-8">
        
        <div className="bg-card border border-border p-6 rounded-xl">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-primary/10 rounded-lg">
              <UploadCloud className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Automated PDF Ingestion</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Upload PDFs and extract questions instantly into the Staging Queue.
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">1. Select Target Subject</label>
              <select 
                value={subjectId} 
                onChange={(e) => setSubjectId(e.target.value)}
                className="w-full h-11 pl-3 pr-8 text-sm bg-background border border-border rounded-md appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[position:right_12px_center] bg-[size:16px] bg-no-repeat focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
              >
                <option value="" disabled>Select a subject...</option>
                {subjects.map((s) => (
                  <option key={s.subject_id} value={s.subject_id}>{s.name}</option>
                ))}
              </select>
            </div>

            <div className="space-y-4">
              <label className="text-sm font-medium">2. Parsing Engine</label>
              <div className="flex gap-4">
                <label className={`flex-1 p-4 border rounded-xl cursor-pointer transition-all ${engine === "llama" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <input type="radio" name="engine" value="llama" checked={engine === "llama"} onChange={() => setEngine("llama")} className="text-primary" />
                    <span className="font-semibold text-sm">LlamaParse + Auto-Image</span>
                  </div>
                  <p className="text-xs text-muted-foreground ml-5">Industry standard for complex PDFs. Rips out embedded diagrams automatically. Lightning fast.</p>
                </label>
                <label className={`flex-1 p-4 border rounded-xl cursor-pointer transition-all ${engine === "ocr" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <input type="radio" name="engine" value="ocr" checked={engine === "ocr"} onChange={() => setEngine("ocr")} className="text-primary" />
                    <span className="font-semibold text-sm">Gemini AI OCR</span>
                  </div>
                  <p className="text-xs text-muted-foreground ml-5">Slower cloud AI extraction. Best for scanned images or PDFs with non-selectable text.</p>
                </label>
              </div>
            </div>

            <div className="space-y-4">
              <label className="text-sm font-medium">3. Provide PDF Source</label>
              
              <div className="flex bg-muted p-1 rounded-lg">
                <button
                  type="button"
                  onClick={() => setUploadMode("file")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-md transition-colors ${uploadMode === "file" ? "bg-background shadow text-foreground" : "text-muted-foreground hover:text-foreground"}`}
                >
                  <FileText className="w-4 h-4" /> Local File
                </button>
                <button
                  type="button"
                  onClick={() => setUploadMode("url")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-md transition-colors ${uploadMode === "url" ? "bg-background shadow text-foreground" : "text-muted-foreground hover:text-foreground"}`}
                >
                  <LinkIcon className="w-4 h-4" /> Web URL
                </button>
              </div>

              {uploadMode === "file" ? (
                <div className="border-2 border-dashed border-border rounded-lg p-8 flex flex-col items-center justify-center gap-3 bg-muted/30 hover:bg-muted/50 transition-colors">
                  <UploadCloud className="w-8 h-8 text-muted-foreground" />
                  <div className="text-sm text-center">
                    <label className="text-primary font-medium cursor-pointer hover:underline">
                      Click to browse
                      <input 
                        type="file" 
                        accept="application/pdf" 
                        className="hidden" 
                        onChange={(e) => setFile(e.target.files[0])}
                      />
                    </label>
                    <span className="text-muted-foreground ml-1">or drag and drop</span>
                  </div>
                  {file && <div className="text-xs font-mono text-emerald-500 bg-emerald-500/10 px-3 py-1 rounded-full">{file.name}</div>}
                </div>
              ) : (
                <div className="space-y-2">
                  <Input 
                    type="url" 
                    placeholder="https://example.com/gate_notes.pdf" 
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="h-11"
                  />
                  <p className="text-xs text-muted-foreground">The backend will securely download this file before processing.</p>
                </div>
              )}
            </div>

            <Button type="submit" disabled={loading} className="w-full h-12 text-base">
              {loading ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : null}
              Start OCR Ingestion
            </Button>
          </form>
        </div>
        
      </div>
    </Layout>
  );
}
