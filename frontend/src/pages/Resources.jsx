import React, { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { FolderArchive, Plus, ExternalLink, Trash2, Upload, FileText, HardDrive, X, Maximize2 } from "lucide-react";
import { toast } from "sonner";
import { Link } from "react-router-dom";

const TYPES = ["Books", "Notes", "Question Banks", "PYQ Collections", "Formula Sheets", "Reference Material"];

function formatSize(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function Resources() {
  const [items, setItems] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [filter, setFilter] = useState({ subject_id: "", resource_type: "" });
  const [openLink, setOpenLink] = useState(false);
  const [openUpload, setOpenUpload] = useState(false);
  const [driveStatus, setDriveStatus] = useState(null);
  const [linkForm, setLinkForm] = useState({ title: "", subject_id: "", resource_type: "Notes", external_url: "" });
  const [uploadForm, setUploadForm] = useState({ title: "", subject_id: "", resource_type: "Notes" });
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [viewer, setViewer] = useState(null); // {title, embed_url, view_url}
  const fileRef = useRef(null);

  const load = () => {
    const params = {};
    Object.entries(filter).forEach(([k, v]) => { if (v) params[k] = v; });
    api.get("/resources", { params }).then(r => setItems(r.data?.data || []));
  };
  useEffect(() => {
    api.get("/subjects").then(r => setSubjects(r.data?.data || []));
    api.get("/drive/status").then(r => setDriveStatus(r.data?.data));
  }, []);
  useEffect(load, [filter]); // eslint-disable-line

  const submitLink = async () => {
    if (!linkForm.title || !linkForm.subject_id) return toast.error("Fill required fields");
    await api.post("/resources", linkForm);
    setOpenLink(false);
    setLinkForm({ title: "", subject_id: "", resource_type: "Notes", external_url: "" });
    load();
    toast.success("Resource added");
  };

  const submitUpload = async () => {
    if (!uploadFile || !uploadForm.subject_id) return toast.error("Pick a file and subject");
    if (!driveStatus?.connected) return toast.error("Connect Google Drive in Settings first");
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", uploadFile);
      fd.append("subject_id", uploadForm.subject_id);
      fd.append("resource_type", uploadForm.resource_type);
      if (uploadForm.title) fd.append("title", uploadForm.title);
      await api.post("/resources/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Uploaded to your Drive");
      setOpenUpload(false);
      setUploadForm({ title: "", subject_id: "", resource_type: "Notes" });
      setUploadFile(null);
      if (fileRef.current) fileRef.current.value = "";
      load();
    } catch (e) {
      toast.error(e?.response?.data?.error?.message || "Upload failed");
    }
    setUploading(false);
  };

  const remove = async (id) => { await api.delete(`/resources/${id}`); load(); };

  const openResource = async (r) => {
    try {
      const res = await api.get(`/resources/${r.resource_id}/view`);
      const data = res.data?.data;
      if (!data?.embed_url) { toast.error("No preview available"); return; }
      setViewer({ title: r.title, embed_url: data.embed_url, view_url: data.view_url, kind: data.kind });
    } catch { toast.error("Could not open"); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Library</div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mt-1">Resources</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Upload from your computer to your own Drive, or link an existing URL. Files live in <code className="mono">GATEPREP/{`{Type}/{Subject}/`}</code>.
          </p>
        </div>
        <div className="flex gap-2">
          <Dialog open={openUpload} onOpenChange={setOpenUpload}>
            <DialogTrigger asChild>
              <Button data-testid="upload-resource-btn">
                <Upload className="w-4 h-4 mr-1" /> Upload from computer
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-card border-border">
              <DialogHeader><DialogTitle>Upload to Google Drive</DialogTitle></DialogHeader>
              {!driveStatus?.connected ? (
                <div className="text-sm space-y-3">
                  <p className="text-muted-foreground">
                    Connect Google Drive to upload from your computer. Files go into <code className="mono">GATEPREP/</code> in your own Drive.
                  </p>
                  <Link to="/settings" className="inline-flex items-center gap-1 text-foreground underline">
                    <HardDrive className="w-3.5 h-3.5" /> Open Settings to connect
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  <input
                    ref={fileRef}
                    type="file"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="block w-full text-sm file:mr-3 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-secondary file:text-foreground hover:file:bg-secondary/80 cursor-pointer"
                    data-testid="upload-file-input"
                  />
                  {uploadFile && (
                    <div className="text-xs mono text-muted-foreground border border-border rounded p-2 flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5" />
                      {uploadFile.name} · {formatSize(uploadFile.size)}
                    </div>
                  )}
                  <Input
                    placeholder="Title (defaults to filename)"
                    value={uploadForm.title}
                    onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })}
                  />
                  <select
                    value={uploadForm.subject_id}
                    onChange={(e) => setUploadForm({ ...uploadForm, subject_id: e.target.value })}
                    className="w-full h-10 px-3 text-sm bg-transparent border border-border rounded-md"
                    data-testid="upload-subject-select"
                  >
                    <option value="">Subject</option>
                    {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
                  </select>
                  <select
                    value={uploadForm.resource_type}
                    onChange={(e) => setUploadForm({ ...uploadForm, resource_type: e.target.value })}
                    className="w-full h-10 px-3 text-sm bg-transparent border border-border rounded-md"
                  >
                    {TYPES.map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
              )}
              {driveStatus?.connected && (
                <DialogFooter>
                  <Button onClick={submitUpload} disabled={uploading || !uploadFile} data-testid="upload-confirm-btn">
                    {uploading ? "Uploading…" : "Upload to my Drive"}
                  </Button>
                </DialogFooter>
              )}
            </DialogContent>
          </Dialog>

          <Dialog open={openLink} onOpenChange={setOpenLink}>
            <DialogTrigger asChild>
              <Button variant="outline" data-testid="add-link-btn"><Plus className="w-4 h-4 mr-1" /> Add by URL</Button>
            </DialogTrigger>
            <DialogContent className="bg-card border-border">
              <DialogHeader><DialogTitle>Add Resource by URL</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <Input placeholder="Title" value={linkForm.title} onChange={e => setLinkForm({ ...linkForm, title: e.target.value })} data-testid="resource-title-input" />
                <select value={linkForm.subject_id} onChange={e => setLinkForm({ ...linkForm, subject_id: e.target.value })} className="w-full h-10 px-3 text-sm bg-transparent border border-border rounded-md" data-testid="resource-subject-select">
                  <option value="">Subject</option>
                  {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
                </select>
                <select value={linkForm.resource_type} onChange={e => setLinkForm({ ...linkForm, resource_type: e.target.value })} className="w-full h-10 px-3 text-sm bg-transparent border border-border rounded-md">
                  {TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
                <Input placeholder="External URL (Google Drive, Dropbox…)" value={linkForm.external_url} onChange={e => setLinkForm({ ...linkForm, external_url: e.target.value })} />
              </div>
              <DialogFooter><Button onClick={submitLink} data-testid="save-resource-btn">Save</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        <select value={filter.subject_id} onChange={e => setFilter({ ...filter, subject_id: e.target.value })} className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All subjects</option>
          {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
        </select>
        <select value={filter.resource_type} onChange={e => setFilter({ ...filter, resource_type: e.target.value })} className="h-9 px-3 text-sm bg-transparent border border-border rounded-md">
          <option value="">All types</option>
          {TYPES.map(t => <option key={t}>{t}</option>)}
        </select>
      </div>

      {items.length === 0 ? (
        <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-12 text-center flex flex-col items-center gap-2">
          <FolderArchive className="w-5 h-5" /> No resources yet.
        </div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-border">
              <tr className="text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                <th className="p-3 font-medium">Title</th>
                <th className="p-3 font-medium">Type</th>
                <th className="p-3 font-medium">Subject</th>
                <th className="p-3 font-medium">Source</th>
                <th className="p-3 font-medium">Size</th>
                <th className="p-3 font-medium">Open</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {items.map(r => {
                const sub = subjects.find(s => s.subject_id === r.subject_id);
                return (
                  <tr key={r.resource_id} className="border-b border-border" data-testid={`resource-${r.resource_id}`}>
                    <td className="p-3">{r.title}</td>
                    <td className="p-3 text-xs mono text-muted-foreground">{r.resource_type}</td>
                    <td className="p-3 text-xs text-muted-foreground">{sub?.name || "—"}</td>
                    <td className="p-3 text-xs">
                      {r.drive_file_id ? (
                        <span className="inline-flex items-center gap-1 text-emerald-500"><HardDrive className="w-3 h-3" /> Drive</span>
                      ) : (
                        <span className="text-muted-foreground">URL</span>
                      )}
                    </td>
                    <td className="p-3 text-xs mono text-muted-foreground">{formatSize(r.file_size)}</td>
                    <td className="p-3">
                      <button onClick={() => openResource(r)} className="text-xs inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" data-testid={`open-resource-${r.resource_id}`}>
                        Open <ExternalLink className="w-3 h-3" />
                      </button>
                    </td>
                    <td className="p-3 text-right">
                      <button onClick={() => remove(r.resource_id)} data-testid={`delete-resource-${r.resource_id}`} className="text-muted-foreground hover:text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {viewer && (
        <div
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-sm flex flex-col"
          data-testid="resource-viewer"
        >
          <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card/90">
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="w-4 h-4 shrink-0" />
              <div className="text-sm font-medium truncate">{viewer.title}</div>
            </div>
            <div className="flex items-center gap-2">
              {viewer.view_url && (
                <a
                  href={viewer.view_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs mono text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                  data-testid="viewer-open-tab"
                >
                  <Maximize2 className="w-3.5 h-3.5" /> open in new tab
                </a>
              )}
              <button
                onClick={() => setViewer(null)}
                className="p-1.5 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground"
                data-testid="viewer-close-btn"
                title="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="flex-1 bg-black">
            <iframe
              src={viewer.embed_url}
              title={viewer.title}
              className="w-full h-full border-0"
              allow="autoplay"
            />
          </div>
        </div>
      )}
    </div>
  );
}
