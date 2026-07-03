import React, { useEffect, useRef, useState, useMemo } from "react";
import { createPortal } from "react-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { FolderArchive, Plus, ExternalLink, Trash2, Upload, FileText, HardDrive, X, Maximize2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import PdfCanvasViewer from "@/components/PdfCanvasViewer";
import Layout from "@/components/Layout";

const TYPES = ["Books", "Notes", "Question Banks", "PYQ Collections", "Formula Sheets", "Reference Material"];
const driveSyncKey = (userId) => (userId ? `driveSyncNeeded:${userId}` : null);

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
  const [viewer, setViewer] = useState(null);
  const [viewerNotes, setViewerNotes] = useState({ content: "", important_pages: [] });
  const fileRef = useRef(null);
  const blobCache = useRef(new Map()); // resource_id -> Blob (cached for this session)
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState(null);
  const closingViewerRef = useRef(false);

  // Group resources by subject in the canonical subject order
  const groups = useMemo(() => {
    const bySubject = new Map();
    for (const item of items) {
      if (!bySubject.has(item.subject_id)) bySubject.set(item.subject_id, []);
      bySubject.get(item.subject_id).push(item);
    }
    return subjects
      .filter(s => bySubject.has(s.subject_id))
      .map(s => ({ subject: s, items: bySubject.get(s.subject_id) }));
  }, [items, subjects]);

  const runSync = async (statusOverride) => {
    if (!statusOverride?.connected) {
      toast.error("Connect Google Drive first (Settings)");
      return;
    }
    setSyncing(true);
    try {
      const r = await api.post("/drive/sync");
      const d = r.data?.data || {};
      setLastSync(d);
      if (d.error === "no_gateprep_folder") {
        toast.info("No existing GATEPREP folder found in your Drive.");
      } else if (d.synced > 0) {
        toast.success(`Restored ${d.synced} file${d.synced === 1 ? "" : "s"} from your Drive`);
        load();
      } else {
        toast.info("Drive is in sync — nothing new to import.");
      }
    } catch (e) {
      toast.error("Drive sync failed: " + (e?.response?.data?.error?.message || e.message));
    }
    setSyncing(false);
  };

  // Revoke blob URL when viewer changes/closes to free memory
  useEffect(() => {
    return () => {
      if (viewer?.isBlob && viewer.embed_url) URL.revokeObjectURL(viewer.embed_url);
    };
  }, [viewer]);

  const closeViewer = () => {
    if (!viewer) return;
    if (window.history.state?.viewerOpen && !closingViewerRef.current) {
      closingViewerRef.current = true;
      window.history.back();
      closingViewerRef.current = false;
    }
    if (viewer?.isBlob && viewer.embed_url) URL.revokeObjectURL(viewer.embed_url);
    setViewer(null);
    setViewerNotes({ content: "", important_pages: [] });
  };

  // Close viewer on Esc
  useEffect(() => {
    if (!viewer) return;
    const onKey = (e) => { if (e.key === "Escape") closeViewer(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [viewer]);

  // Push a history entry when the viewer opens so the browser back button
  // closes the viewer instead of navigating to the previous page.
  useEffect(() => {
    if (viewer) {
      window.history.pushState({ viewerOpen: true }, "");
    }
  }, [viewer]);

  useEffect(() => {
    const handlePopState = () => {
      if (viewer && !closingViewerRef.current) {
        if (viewer?.isBlob && viewer.embed_url) URL.revokeObjectURL(viewer.embed_url);
        setViewer(null);
        setViewerNotes({ content: "", important_pages: [] });
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [viewer]);

  const load = () => {
    const params = {};
    Object.entries(filter).forEach(([k, v]) => { if (v) params[k] = v; });
    api.get("/resources", { params }).then(r => setItems(r.data?.data || []));
  };
  useEffect(() => {
    api.get("/subjects").then(r => setSubjects(r.data?.data || []));
    api.get("/drive/status").then(r => {
      const status = r.data?.data;
      setDriveStatus(status);
      if (status?.connected) {
        // Refresh the Drive token silently in the background so opening PDFs is instant.
        api.post("/drive/refresh").catch(() => {});

        // Sync only on first visit after login or explicit user action.
        const syncKey = driveSyncKey(status.user_id);
        if (syncKey && localStorage.getItem(syncKey) === "true") {
          localStorage.removeItem(syncKey);
          runSync(status);
        }
      }
    });
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
      runSync(driveStatus);
    } catch (e) {
      toast.error(e?.response?.data?.error?.message || "Upload failed");
    }
    setUploading(false);
  };

  const remove = async (id) => { await api.delete(`/resources/${id}`); load(); };

  const openResource = async (r) => {
    try {
      // Fetch notes + important pages in parallel with the view url request
      const notesPromise = api.get(`/resources/${r.resource_id}/notes`).then(
        (resp) => resp.data?.data || { content: "", important_pages: [] },
      ).catch(() => ({ content: "", important_pages: [] }));

      const res = await api.get(`/resources/${r.resource_id}/view`);
      const data = res.data?.data;
      if (!data?.embed_url && data?.kind !== "drive") { toast.error("No preview available"); return; }

      // Resolve notes (don't block UI on it though — viewer can render while notes load)
      notesPromise.then((n) => setViewerNotes({
        content: n.content || "",
        important_pages: Array.isArray(n.important_pages) ? n.important_pages : [],
      }));

      if (data.kind === "drive") {
        const cached = blobCache.current.get(r.resource_id);
        if (cached) {
          const isPdf = (cached.type || "").includes("pdf") || r.title?.toLowerCase().endsWith(".pdf");
          if (isPdf) {
            setViewer({ resource_id: r.resource_id, title: r.title, blob: cached, view_url: data.view_url, isPdf: true, loading: false });
          } else {
            const blobUrl = URL.createObjectURL(cached);
            setViewer({ resource_id: r.resource_id, title: r.title, embed_url: blobUrl, view_url: data.view_url, isBlob: true, loading: false });
          }
          return;
        }
        setViewer({ resource_id: r.resource_id, title: r.title, blob: null, view_url: data.view_url, isPdf: true, loading: true });
        const blobRes = await api.get(`/resources/${r.resource_id}/stream`, { responseType: "blob" });
        blobCache.current.set(r.resource_id, blobRes.data);
        const isPdf = (blobRes.data?.type || "").includes("pdf") || r.title?.toLowerCase().endsWith(".pdf");
        if (isPdf) {
          setViewer({ resource_id: r.resource_id, title: r.title, blob: blobRes.data, view_url: data.view_url, isPdf: true, loading: false });
        } else {
          const blobUrl = URL.createObjectURL(blobRes.data);
          setViewer({ resource_id: r.resource_id, title: r.title, embed_url: blobUrl, view_url: data.view_url, isBlob: true, loading: false });
        }
      } else {
        setViewer({ resource_id: r.resource_id, title: r.title, embed_url: data.embed_url, view_url: data.view_url, isBlob: false, loading: false });
      }
    } catch (e) {
      const status = e?.response?.status;
      const code = e?.response?.data?.error?.code;
      const message = e?.response?.data?.error?.message;
      if (status === 401 || code === "drive_access_denied") {
        toast.error("Drive access expired — reconnect in Settings");
      } else if (message) {
        toast.error(message);
      } else {
        toast.error("Could not open");
      }
      setViewer(null);
    }
  };

  // ---- Notes & important-page handlers (passed into PdfCanvasViewer) ----
  const saveNotesContent = async (content) => {
    if (!viewer?.resource_id) return;
    try {
      const resp = await api.post(`/resources/${viewer.resource_id}/notes`, { content });
      const d = resp.data?.data;
      if (d) setViewerNotes({
        content: d.content || "",
        important_pages: Array.isArray(d.important_pages) ? d.important_pages : [],
      });
    } catch {
      toast.error("Couldn't save notes");
    }
  };

  const togglePage = async (page) => {
    if (!viewer?.resource_id) return;
    // Optimistic update
    const had = (viewerNotes.important_pages || []).some((p) => p.page === page);
    const next = had
      ? viewerNotes.important_pages.filter((p) => p.page !== page)
      : [...viewerNotes.important_pages, { page, label: "" }].sort((a, b) => a.page - b.page);
    setViewerNotes((v) => ({ ...v, important_pages: next }));
    try {
      const resp = await api.post(`/resources/${viewer.resource_id}/pages/toggle`, { page });
      const pages = resp.data?.data?.important_pages;
      if (Array.isArray(pages)) setViewerNotes((v) => ({ ...v, important_pages: pages }));
    } catch {
      toast.error("Couldn't update bookmark");
      // Revert on failure
      setViewerNotes((v) => ({ ...v, important_pages: viewerNotes.important_pages }));
    }
  };

  const updatePageLabel = async (page, label) => {
    if (!viewer?.resource_id) return;
    setViewerNotes((v) => ({
      ...v,
      important_pages: v.important_pages.map((p) => (p.page === page ? { ...p, label } : p)),
    }));
    try {
      const resp = await api.post(`/resources/${viewer.resource_id}/pages/label`, { page, label });
      const pages = resp.data?.data?.important_pages;
      if (Array.isArray(pages)) setViewerNotes((v) => ({ ...v, important_pages: pages }));
    } catch {
      toast.error("Couldn't save label");
    }
  };

  return (
    <Layout title={viewer ? viewer.title : "Resources"} hideSidebar={!!viewer}>
      {viewer ? (
        <div
          className="dark bg-[#0a0a0a] flex flex-col h-screen w-full overflow-hidden"
          data-testid="resource-viewer"
        >
          {viewer.loading ? (
            <div className="flex-1 bg-card/5 relative min-h-0 flex flex-col items-center justify-center gap-3 text-muted-foreground">
              <div className="w-8 h-8 border-2 border-border border-t-primary rounded-full animate-spin" />
              <div className="text-xs font-mono">Streaming from your Drive…</div>
            </div>
          ) : viewer.isPdf && viewer.blob ? (
            <PdfCanvasViewer
              blob={viewer.blob}
              notes={viewerNotes.content}
              importantPages={viewerNotes.important_pages}
              onNotesChange={saveNotesContent}
              onTogglePage={togglePage}
              onUpdateLabel={updatePageLabel}
              title={viewer.title}
              onClose={closeViewer}
            />
          ) : (
            <div className="flex-1 flex flex-col min-h-0">
              <div className="flex items-center justify-between px-5 py-2.5 border-b border-border bg-card/30 shrink-0">
                <div className="flex items-center gap-2 min-w-0">
                  <button
                    onClick={closeViewer}
                    className="h-8 px-3 inline-flex items-center justify-center rounded-md border border-border hover:bg-secondary/50 text-xs font-semibold text-foreground transition-colors mr-2"
                  >
                    ← Back to Library
                  </button>
                  <FileText className="w-4 h-4 shrink-0 text-muted-foreground" />
                  <div className="text-sm font-medium truncate text-foreground">{viewer.title}</div>
                </div>
                {viewer.view_url && (
                  <a
                    href={viewer.view_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-mono text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 px-2.5 h-8 rounded-md hover:bg-secondary/50 transition-colors"
                    data-testid="viewer-open-tab"
                  >
                    <Maximize2 className="w-3.5 h-3.5" /> open in new tab
                  </a>
                )}
              </div>
              <iframe
                src={viewer.embed_url}
                title={viewer.title}
                className="flex-1 w-full border-0 bg-white"
                allow="autoplay"
              />
            </div>
          )}
        </div>
      ) : (
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
            <select value={filter.subject_id} onChange={e => setFilter({ ...filter, subject_id: e.target.value })} className="h-9 pl-3 pr-10 text-sm bg-transparent border border-border rounded-md appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[position:right_12px_center] bg-[size:16px] bg-no-repeat">
              <option value="">All subjects</option>
              {subjects.map(s => <option key={s.subject_id} value={s.subject_id}>{s.name}</option>)}
            </select>
            <select value={filter.resource_type} onChange={e => setFilter({ ...filter, resource_type: e.target.value })} className="h-9 pl-3 pr-10 text-sm bg-transparent border border-border rounded-md appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[position:right_12px_center] bg-[size:16px] bg-no-repeat">
              <option value="">All types</option>
              {TYPES.map(t => <option key={t}>{t}</option>)}
            </select>
          </div>

          {syncing && (
            <div className="text-xs mono text-muted-foreground border border-border rounded px-3 py-2 flex items-center gap-2">
              <RefreshCw className="w-3 h-3 animate-spin" />
              Syncing Drive files…
            </div>
          )}

          {lastSync && (
            <div className="text-xs mono text-muted-foreground border border-border rounded px-3 py-2">
              Last Drive sync: <span className="text-foreground">{lastSync.synced}</span> restored,{" "}
              <span className="text-foreground">{lastSync.skipped}</span> already tracked
              {Array.isArray(lastSync.unknown_subjects) && lastSync.unknown_subjects.length > 0 && (
                <div className="mt-1 text-amber-500">
                  Skipped folders (no matching subject): {lastSync.unknown_subjects.join(", ")}
                </div>
              )}
            </div>
          )}

          {items.length === 0 ? (
            <div className="text-sm text-muted-foreground border border-dashed border-border rounded-lg p-12 text-center flex flex-col items-center gap-2">
              <FolderArchive className="w-5 h-5" /> No resources yet.
            </div>
          ) : (
            <div className="space-y-10">
              {groups.map(({ subject, items: subjectItems }) => (
                <section key={subject.subject_id} data-testid={`resource-group-${subject.subject_id}`}>
                  <div className="flex items-baseline justify-between border-b border-border pb-2 mb-4">
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mono">
                        Subject · {String(subject.order + 1).padStart(2, "0")}
                      </div>
                      <h2 className="text-lg font-semibold tracking-tight mt-0.5">{subject.name}</h2>
                    </div>
                    <div className="text-xs mono text-muted-foreground">
                      {subjectItems.length} resource{subjectItems.length > 1 ? "s" : ""}
                    </div>
                  </div>
                  <div className="border border-border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="border-b border-border">
                        <tr className="text-left text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                          <th className="p-3 font-medium">Title</th>
                          <th className="p-3 font-medium">Type</th>
                          <th className="p-3 font-medium">Source</th>
                          <th className="p-3 font-medium">Size</th>
                          <th className="p-3 font-medium">Open</th>
                          <th className="p-3"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {subjectItems.map(r => (
                          <tr key={r.resource_id} className="border-b border-border hover:bg-muted/30 transition-colors" data-testid={`resource-${r.resource_id}`}>
                            <td className="p-3 font-medium">{r.title}</td>
                            <td className="p-3 text-xs mono text-muted-foreground">{r.resource_type}</td>
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
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              ))}
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
