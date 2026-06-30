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
  const [source, setSource] = useState(""); // e.g. "GO-PDFs", "MADE Easy", etc.
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
      formData.append("engine", "mistral");
      formData.append("source", source.trim());
      if (uploadMode === "file") {
        formData.append("file", file);
      } else {
        formData.append("url", url);
      }

      await api.post("/data/import/pdf", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      
      toast.success("PDF sent to Mistral OCR pipeline. Check Staging Queue!");
      navigate("/admin/staging");
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || "Failed to start import.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="Import PDF">
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
            {/* 1. Subject */}
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

            {/* 2. Source label */}
            <div className="space-y-2">
              <label className="text-sm font-medium">2. Source / Publisher <span className="text-muted-foreground font-normal">(optional)</span></label>
              <Input
                type="text"
                placeholder="e.g. GO-PDFs, MADE Easy, ACE Academy, Self-Made…"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="h-11"
              />
              <p className="text-xs text-muted-foreground">
                This tag will appear on every question imported from this PDF. Leave blank if not applicable.
              </p>
            </div>

            {/* 3. OCR Engine info */}
            <div className="space-y-2">
              <label className="text-sm font-medium">3. Ingestion Engine</label>
              <div className="p-4 border border-primary/20 bg-primary/5 rounded-xl">
                <div className="font-semibold text-sm text-primary">Mistral AI OCR</div>
                <p className="text-xs text-muted-foreground mt-1">State-of-the-art layout-aware document OCR. High-precision KaTeX math formatting and relational solution stitching.</p>
              </div>
            </div>

            {/* 4. PDF Source */}
            <div className="space-y-4">
              <label className="text-sm font-medium">4. Provide PDF</label>
              
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
